"""
Optional LLM extractor using Google Gemini (free tier, no credit card needed).

If GEMINI_API_KEY is not set, is_available() returns False and the pipeline
simply skips this extractor. When it IS set, we ask the model to return the
exact same JSON schema as the rule-based extractor, so the two are directly
comparable for Paper 1.

We call the REST endpoint with `requests` to avoid an extra SDK dependency.
"""
import json
import re

import config
from collectors.base import _session  # reuse the polite session

ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"
            "{model}:generateContent")

SCHEMA_FIELDS = [
    "pathogens", "antibiotics", "resistance_genes", "diseases",
    "countries", "regions", "keywords", "event_type", "study_type", "summary",
]

PROMPT = """You are an infectious-disease and antimicrobial-resistance (AMR) information extraction assistant.
Read the document below and return ONLY a JSON object (no markdown fence, no commentary) with these keys:

- "pathogens": list of pathogens, using standard labels where possible (e.g. "MRSA", "VRE", "CRE", "CRAB", "Candida auris", "Klebsiella pneumoniae").
- "antibiotics": list of antibiotics/antifungals mentioned.
- "resistance_genes": list of resistance genes/mechanisms (e.g. "NDM", "KPC", "OXA-48", "vanA", "mecA").
- "diseases": list of infections/syndromes (e.g. "bloodstream infection", "pneumonia").
- "countries": list of countries explicitly involved.
- "regions": list from ["APAC","Americas","Europe","MENA","Africa","Other"].
- "keywords": up to 12 concise keywords.
- "event_type": exactly one of ["Outbreak","Antimicrobial Resistance","Emerging Pathogen","Vaccine","New Drug","Clinical Trial","Guideline","Research Article"].
- "study_type": one of ["Paper","Guideline","Clinical Trial","Outbreak","News"].
- "summary": a 200-300 word plain-English summary for an ID clinician.

If a field has nothing, use an empty list (or empty string for summary). Do not invent facts.

SOURCE: {source}
TITLE: {title}

DOCUMENT:
{body}
"""


def is_available() -> bool:
    return bool(config.GEMINI_API_KEY)


def name() -> str:
    return config.GEMINI_MODEL


def _coerce(obj: dict) -> dict:
    out = {}
    for f in SCHEMA_FIELDS:
        val = obj.get(f)
        if f in ("event_type", "study_type", "summary"):
            out[f] = val if isinstance(val, str) else ""
        else:
            if isinstance(val, list):
                out[f] = [str(x).strip() for x in val if str(x).strip()]
            elif isinstance(val, str) and val.strip():
                out[f] = [val.strip()]
            else:
                out[f] = []
    return out


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # Grab the outermost JSON object if the model added stray text.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def extract(title: str, text: str, source: str = "", max_retries: int = 3) -> tuple[dict, str]:
    """Returns (structured_result, raw_output_text). Raises on hard failure.

    Retries on HTTP 429 (rate limit) with a short backoff so a full-corpus run
    survives free-tier limits instead of crashing.
    """
    import time
    body = (text or "")[:8000]  # keep prompt small / free-tier friendly
    prompt = PROMPT.format(source=source, title=title, body=body)
    url = ENDPOINT.format(model=config.GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "response_mime_type": "application/json"},
    }
    resp = None
    for attempt in range(max_retries + 1):
        resp = _session.post(url, params={"key": config.GEMINI_API_KEY},
                             json=payload, timeout=config.HTTP_TIMEOUT)
        if resp.status_code == 429 and attempt < max_retries:
            wait = float(resp.headers.get("Retry-After", 0)) or (8 * (attempt + 1))
            time.sleep(wait)
            continue
        break
    resp.raise_for_status()
    data = resp.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = _coerce(_parse_json(raw))
    return parsed, raw
