"""
PubMed collector via NCBI E-utilities (free, no key required).

esearch -> list of PMIDs for each query (restricted to a recent date window)
efetch  -> XML with title + abstract + journal + publication date
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import config
from collectors.base import get

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _key_params():
    return {"api_key": config.NCBI_API_KEY} if config.NCBI_API_KEY else {}


def _search(query: str, max_ids: int) -> list[str]:
    mindate = (datetime.utcnow() - timedelta(days=config.PUBMED_LOOKBACK_DAYS)).strftime("%Y/%m/%d")
    maxdate = datetime.utcnow().strftime("%Y/%m/%d")
    params = {
        "db": "pubmed", "term": query, "retmax": max_ids, "retmode": "json",
        "datetype": "pdat", "mindate": mindate, "maxdate": maxdate,
        "sort": "most+recent", **_key_params(),
    }
    data = get(ESEARCH, params=params).json()
    return data.get("esearchresult", {}).get("idlist", [])


def _pubdate(article: ET.Element) -> str | None:
    pd = article.find(".//PubDate")
    if pd is None:
        return None
    year = pd.findtext("Year")
    if not year:
        medline = pd.findtext("MedlineDate")  # e.g. "2026 Jun-Jul"
        if medline:
            year = medline.split()[0]
    if not year:
        return None
    month_txt = pd.findtext("Month") or "1"
    day = pd.findtext("Day") or "1"
    months = {m: i for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    month = months.get(month_txt[:3], None) or (int(month_txt) if month_txt.isdigit() else 1)
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        return f"{year}-01-01"


def _fetch_details(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", **_key_params()}
    xml = get(EFETCH, params=params).text
    root = ET.fromstring(xml)
    docs = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID")
        title = art.findtext(".//ArticleTitle") or ""
        # Abstract may have multiple labelled sections.
        abstract_parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            text = "".join(ab.itertext()).strip()
            abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = "\n".join(p for p in abstract_parts if p)
        journal = art.findtext(".//Journal/Title") or ""
        raw = f"{title}\n\n{abstract}".strip()
        if journal:
            raw += f"\n\nJournal: {journal}"
        docs.append({
            "source": "PubMed",
            "source_id": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "title": title,
            "raw_text": raw,
            "published_date": _pubdate(art),
        })
    return docs


def collect() -> list[dict]:
    seen, docs = set(), []
    for query in config.PUBMED_QUERIES:
        try:
            ids = _search(query, config.PUBMED_MAX_PER_QUERY)
            fresh = [i for i in ids if i not in seen]
            seen.update(fresh)
            docs.extend(_fetch_details(fresh))
        except Exception as exc:  # noqa: BLE001
            print(f"  [PubMed] query '{query}' failed: {exc}")
    return docs
