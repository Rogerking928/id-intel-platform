"""
ClinicalTrials.gov collector via the public API v2 (free, no key).
https://clinicaltrials.gov/api/v2/studies
"""
import config
from collectors.base import get

API = "https://clinicaltrials.gov/api/v2/studies"


def _study_to_doc(study: dict) -> dict | None:
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    nct = ident.get("nctId")
    if not nct:
        return None
    title = ident.get("briefTitle") or ident.get("officialTitle") or ""
    desc = ps.get("descriptionModule", {})
    summary = desc.get("briefSummary", "")
    conditions = ps.get("conditionsModule", {}).get("conditions", [])
    interventions = [
        i.get("name", "") for i in
        ps.get("armsInterventionsModule", {}).get("interventions", [])
    ]
    locations = ps.get("contactsLocationsModule", {}).get("locations", [])
    countries = sorted({loc.get("country") for loc in locations if loc.get("country")})
    status_mod = ps.get("statusModule", {})
    date = (status_mod.get("startDateStruct", {}).get("date")
            or status_mod.get("lastUpdatePostDateStruct", {}).get("date"))
    # Normalise "2026-06" -> "2026-06-01"
    if date and len(date) == 7:
        date = date + "-01"

    raw = "\n".join(filter(None, [
        title,
        f"Conditions: {', '.join(conditions)}" if conditions else "",
        f"Interventions: {', '.join(interventions)}" if interventions else "",
        f"Countries: {', '.join(countries)}" if countries else "",
        summary,
    ]))
    return {
        "source": "ClinicalTrials",
        "source_id": nct,
        "url": f"https://clinicaltrials.gov/study/{nct}",
        "title": title,
        "raw_text": raw,
        "published_date": date,
    }


def collect() -> list[dict]:
    seen, docs = set(), []
    for term in config.CT_QUERIES:
        try:
            params = {
                "query.term": term,
                "pageSize": config.CT_MAX_STUDIES,
                "sort": "LastUpdatePostDate:desc",
                "format": "json",
            }
            studies = get(API, params=params).json().get("studies", [])
            for s in studies:
                doc = _study_to_doc(s)
                if doc and doc["source_id"] not in seen:
                    seen.add(doc["source_id"])
                    docs.append(doc)
        except Exception as exc:  # noqa: BLE001
            print(f"  [ClinicalTrials] term '{term}' failed: {exc}")
    return docs
