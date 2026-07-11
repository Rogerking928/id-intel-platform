"""Backfill a dated PubMed corpus for VIGIL's external-validation study.

Example (bounded, reproducible historical collection):
    python backfill_pubmed.py --start-year 2019 --end-year 2023 --max-per-query 100 --extract

The script uses publication-date windows, records public PubMed metadata and
abstracts, and relies on the database's source/id constraint for safe re-runs.
"""
from __future__ import annotations

import argparse
import time

import db
from collectors import pubmed
from collectors.base import get


def search_year(query: str, year: int, max_ids: int) -> list[str]:
    params = {
        "db": "pubmed", "term": query, "retmax": max_ids, "retmode": "json",
        "datetype": "pdat", "mindate": f"{year}/01/01", "maxdate": f"{year}/12/31",
        "sort": "most+recent", **pubmed._key_params(),
    }
    payload = get(pubmed.ESEARCH, params=params).json()
    return payload.get("esearchresult", {}).get("idlist", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill dated PubMed AMR documents.")
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--max-per-query", type=int, default=100)
    parser.add_argument("--extract", action="store_true",
                        help="Run VIGIL extraction after collection.")
    args = parser.parse_args()
    if args.start_year > args.end_year or args.max_per_query < 1:
        parser.error("Check year order and max-per-query.")

    db.init_db()
    seen, fetched, inserted = set(), 0, 0
    for year in range(args.start_year, args.end_year + 1):
        for query in pubmed.config.PUBMED_QUERIES:
            ids = [pmid for pmid in search_year(query, year, args.max_per_query) if pmid not in seen]
            seen.update(ids)
            docs = pubmed._fetch_details(ids)
            fetched += len(docs)
            new = 0
            for doc in docs:
                _id, is_new = db.upsert_document(doc)
                new += int(is_new)
            inserted += new
            print(f"{year} | {query}: fetched={len(docs)} new={new}")
            time.sleep(0.4 if not pubmed.config.NCBI_API_KEY else 0.12)
    print(f"Backfill complete: fetched={fetched}, newly stored={inserted}.")
    if args.extract:
        from extract import pipeline
        print("Running deterministic extraction / graph rebuild for new documents...")
        print(pipeline.run())


if __name__ == "__main__":
    main()
