"""
Generic RSS collector used for CDC and ECDC feeds.

feedparser handles the parsing; we just normalise into our document dict and
tag the source. If a feed URL is dead, we skip it without crashing the run.
"""
import re

import feedparser

import config


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _entry_date(entry) -> str | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"
    return None


def _collect_feeds(source: str, feeds: list[str]) -> list[dict]:
    docs, seen = [], set()
    for url in feeds:
        try:
            parsed = feedparser.parse(url, agent=config.USER_AGENT)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{source}] feed failed {url}: {exc}")
            continue
        for e in parsed.entries:
            link = e.get("link", "")
            sid = e.get("id") or link or e.get("title", "")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            title = _clean(e.get("title", ""))
            summary = _clean(e.get("summary", "") or e.get("description", ""))
            docs.append({
                "source": source,
                "source_id": sid,
                "url": link,
                "title": title,
                "raw_text": f"{title}\n\n{summary}".strip(),
                "published_date": _entry_date(e),
            })
    return docs


def collect_cdc() -> list[dict]:
    return _collect_feeds("CDC", config.CDC_FEEDS)


def collect_ecdc() -> list[dict]:
    return _collect_feeds("ECDC", config.ECDC_FEEDS)
