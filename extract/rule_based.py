"""
Rule-based / dictionary extractor. This is the ALWAYS-ON, free, offline
extractor and also the Paper 1 baseline (dictionary + regex, comparable to a
scispaCy gazetteer baseline).

Given a document's text it returns the same structured schema the LLM returns:
    pathogens, antibiotics, resistance_genes, diseases, countries, regions,
    keywords, event_type, study_type, summary
"""
import re

from extract import dictionaries as dic


def _find_terms(text_low: str, table: dict[str, list[str]]) -> list[str]:
    """Return canonical terms whose any synonym appears in text (word-ish boundary)."""
    hits = []
    for canonical, synonyms in table.items():
        for syn in synonyms:
            # \b works for alphanumerics; many terms contain '-' so we build a
            # lenient boundary that still avoids matching inside a longer word.
            pattern = r"(?<![a-z0-9])" + re.escape(syn.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, text_low):
                hits.append(canonical)
                break
    return hits


def _find_countries(text: str) -> tuple[list[str], list[str]]:
    countries, regions = [], set()
    for country, region in dic.COUNTRY_REGION.items():
        pattern = r"\b" + re.escape(country) + r"\b"
        if re.search(pattern, text):  # case-sensitive: country names are capitalised
            countries.append(country)
            regions.add(region)
    return sorted(set(countries)), sorted(regions)


def classify_event_type(text_low: str, source: str) -> str:
    """Assign one of the 8 event categories using keyword hints + source prior."""
    if source == "WHO":
        return "Outbreak"
    if source == "ClinicalTrials":
        return "Clinical Trial"
    scores = {}
    for etype in dic.EVENT_TYPE_ORDER:
        hints = dic.EVENT_TYPE_HINTS.get(etype, [])
        scores[etype] = sum(1 for h in hints if h in text_low)
    best = max(dic.EVENT_TYPE_ORDER, key=lambda e: scores[e])
    if scores[best] == 0:
        return "Research Article"
    return best


def classify_study_type(text_low: str, source: str) -> str:
    if source == "ClinicalTrials":
        return "Clinical Trial"
    if source == "WHO":
        return "Outbreak"
    for stype, hints in dic.STUDY_TYPE_HINTS.items():
        if any(h in text_low for h in hints):
            return stype
    if source in ("PubMed",):
        return "Paper"
    return "News"


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _extractive_summary(text: str, max_chars: int = 700) -> str:
    """Baseline summary = first few sentences, capped. The LLM does the real thing."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    out, total = [], 0
    for sent in _SENT_SPLIT.split(text):
        if total + len(sent) > max_chars:
            break
        out.append(sent)
        total += len(sent) + 1
    return " ".join(out) if out else text[:max_chars]


def _keywords(pathogens, genes, antibiotics, diseases, event_type) -> list[str]:
    kws = []
    for group in (pathogens, genes, antibiotics, diseases):
        kws.extend(group)
    if event_type:
        kws.append(event_type)
    # de-dup preserving order
    seen, out = set(), []
    for k in kws:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:15]


def extract(title: str, text: str, source: str = "") -> dict:
    full = f"{title}\n{text}".strip()
    low = full.lower()

    pathogens = _find_terms(low, dic.PATHOGENS)
    antibiotics = _find_terms(low, dic.ANTIBIOTICS)
    genes = _find_terms(low, dic.RESISTANCE_GENES)
    diseases = _find_terms(low, dic.DISEASES)
    countries, regions = _find_countries(full)
    event_type = classify_event_type(low, source)
    study_type = classify_study_type(low, source)

    return {
        "pathogens": pathogens,
        "antibiotics": antibiotics,
        "resistance_genes": genes,
        "diseases": diseases,
        "countries": countries,
        "regions": regions,
        "keywords": _keywords(pathogens, genes, antibiotics, diseases, event_type),
        "event_type": event_type,
        "study_type": study_type,
        "summary": _extractive_summary(text or title),
    }
