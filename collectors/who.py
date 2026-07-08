"""
WHO Disease Outbreak News collector via the site's JSON (OData) API.

The old RSS feed is dead (returns a JS page). This endpoint is what the WHO
website itself calls, and it exposes the rich narrative fields.
"""
import re

import config
from collectors.base import get


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    return re.sub(r"\s+", " ", text).strip()


def collect() -> list[dict]:
    params = {
        "sf_provider": "dynamicProvider372",
        "sf_culture": "en",
        "$orderby": "PublicationDateAndTime desc",
        "$top": config.WHO_MAX_ITEMS,
        "$select": ("Title,PublicationDateAndTime,UrlName,Summary,Overview,"
                    "Epidemiology,Assessment,Advice"),
        "$format": "json",
    }
    try:
        items = get(config.WHO_DON_API, params=params).json().get("value", [])
    except Exception as exc:  # noqa: BLE001
        print(f"  [WHO] API failed: {exc}")
        return []

    docs = []
    for it in items:
        url_name = it.get("UrlName")
        if not url_name:
            continue
        pub = it.get("PublicationDateAndTime") or ""
        published = pub[:10] if len(pub) >= 10 else None
        body = " ".join(_strip_html(it.get(f, "")) for f in
                        ("Summary", "Overview", "Epidemiology", "Assessment", "Advice"))
        title = it.get("Title", "")
        docs.append({
            "source": "WHO",
            "source_id": url_name,
            "url": config.WHO_DON_ITEM_URL + url_name,
            "title": title,
            "raw_text": f"{title}\n\n{body}".strip(),
            "published_date": published,
        })
    return docs
