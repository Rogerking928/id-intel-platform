"""
WHO GLASS (Global AMR Surveillance) collector.

GLASS does not expose a simple per-record public API the way PubMed or
ClinicalTrials do — the data comes as country reports / dashboard exports.
So this collector is a structured placeholder:

  * If you drop a CSV at data/glass_manual.csv it will be imported. Expected
    columns (any subset): title, country, pathogen, antibiotic, year, url, text.
  * Otherwise it is a no-op and the daily run continues.

This keeps the pipeline shape complete so real GLASS ingestion can be added
later without touching the rest of the platform.
"""
import csv

import config


def collect() -> list[dict]:
    path = config.DATA_DIR / "glass_manual.csv"
    if not path.exists():
        print("  [GLASS] no data/glass_manual.csv found - skipping (this is fine for the MVP).")
        return []

    docs = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            title = row.get("title") or f"GLASS record {i+1}"
            parts = [title]
            for col in ("country", "pathogen", "antibiotic", "text"):
                if row.get(col):
                    parts.append(f"{col.title()}: {row[col]}")
            year = row.get("year")
            docs.append({
                "source": "GLASS",
                "source_id": row.get("url") or f"glass-{i+1}",
                "url": row.get("url", ""),
                "title": title,
                "raw_text": "\n".join(parts),
                "published_date": f"{year}-01-01" if year else None,
            })
    print(f"  [GLASS] imported {len(docs)} rows from glass_manual.csv")
    return docs
