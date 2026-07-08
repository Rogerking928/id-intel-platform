"""
Preprint collector via Europe PMC (free, no key).

Europe PMC indexes bioRxiv + medRxiv preprints and supports keyword search, so
it is a cleaner way to pull AMR-relevant preprints than each preprint server's
own date-only API. We restrict to SRC:PPR (preprints).
https://europepmc.org/RestfulWebService
"""
import re

import config
from collectors.base import get

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _strip(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def _result_to_doc(r: dict) -> dict | None:
    pid = r.get("id")
    src = r.get("source", "PPR")
    if not pid:
        return None
    title = _strip(r.get("title", "")).rstrip(".")
    abstract = _strip(r.get("abstractText", ""))
    doi = r.get("doi")
    url = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/{src}/{pid}"
    date = r.get("firstPublicationDate")  # already YYYY-MM-DD
    raw = f"{title}\n\n{abstract}".strip()
    return {
        "source": "Preprint",
        "source_id": f"{src}:{pid}",
        "url": url,
        "title": title,
        "raw_text": raw,
        "published_date": date,
    }


def collect() -> list[dict]:
    seen, docs = set(), []
    for query in config.EUROPEPMC_QUERIES:
        try:
            params = {
                "query": f"({query}) AND SRC:PPR",
                "resultType": "core",
                "format": "json",
                "pageSize": config.EUROPEPMC_MAX,
                "sort": "P_PDATE_D desc",
            }
            results = get(API, params=params).json().get("resultList", {}).get("result", [])
            for r in results:
                doc = _result_to_doc(r)
                if doc and doc["source_id"] not in seen:
                    seen.add(doc["source_id"])
                    docs.append(doc)
        except Exception as exc:  # noqa: BLE001
            print(f"  [EuropePMC] query '{query}' failed: {exc}")
    return docs
