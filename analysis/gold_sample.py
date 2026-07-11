"""Frozen gold-standard sample for the Paper 1 extraction benchmark.

Why this file exists
--------------------
A benchmark needs a *fixed, shared* set of documents:
  * both annotators must label the SAME documents (otherwise Cohen's kappa is
    undefined), and
  * the set must be frozen BEFORE anyone inspects model output (leakage control,
    see docs/CODEBOOK.md section 8).

`build()` draws a deterministic, stratified sample and writes it to
`docs/gold_sample.csv` (committed, auditable). `load_ids()` reads it back and maps
to the current database by URL, so it is robust to id changes.

Sampling frame (transparent, disclosed in the paper)
----------------------------------------------------
The sample is *purposively enriched* for AMR content so the benchmark actually
exercises the resistance-mechanism and pathogen fields; it is therefore NOT a
prevalence-representative sample, and we say so. Strata, in priority order:
  1. every official alert from the small authoritative sources (WHO, ECDC, UKHSA);
  2. AMR-enriched: documents carrying a resistance-mechanism entity or an
     'Antimicrobial Resistance' event type;
  3. outbreak documents;
  4. a stratified random fill across the remaining sources (CDC, PubMed,
     preprints, ClinicalTrials) up to the target size.
A single fixed seed makes the draw reproducible.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

import db

SEED = 20260711          # fixed — do not change once annotation has begun
DEFAULT_N = 150
CSV_PATH = Path(__file__).resolve().parent.parent / "docs" / "gold_sample.csv"
SMALL_SOURCES = ("WHO", "ECDC", "UKHSA")


def _all_docs() -> list[dict]:
    with db.get_conn() as conn:
        docs = [dict(r) for r in conn.execute(
            "SELECT id, url, source, title FROM documents WHERE url != ''").fetchall()]
        amr = {r[0] for r in conn.execute(
            "SELECT DISTINCT document_id FROM entities WHERE entity_type='resistance_gene'")}
        ev = {r["document_id"]: r["event_type"] for r in conn.execute(
            "SELECT document_id, event_type FROM extractions WHERE is_active=1")}
    for d in docs:
        d["is_amr"] = d["id"] in amr or ev.get(d["id"]) == "Antimicrobial Resistance"
        d["event_type"] = ev.get(d["id"])
    return docs


def build(n: int = DEFAULT_N, seed: int = SEED) -> Path:
    docs = _all_docs()
    rng = random.Random(seed)
    by_id = {d["id"]: d for d in docs}
    picked: list[int] = []
    seen: set[int] = set()

    def take(pool, k, stratum):
        pool = [d for d in pool if d["id"] not in seen]
        rng.shuffle(pool)
        for d in pool[:k]:
            d["_stratum"] = stratum
            picked.append(d["id"]); seen.add(d["id"])

    # 1. all official alerts from the small authoritative sources
    take([d for d in docs if d["source"] in SMALL_SOURCES], 10**9, "official-alert")
    # 2. AMR-enriched
    take([d for d in docs if d["is_amr"]], max(0, n // 3), "amr-enriched")
    # 3. outbreaks
    take([d for d in docs if d["event_type"] == "Outbreak"], max(0, n // 6), "outbreak")
    # 4. stratified random fill across remaining sources
    remaining_sources = ["CDC", "PubMed", "Preprint", "ClinicalTrials"]
    while len(picked) < n:
        added = 0
        for src in remaining_sources:
            if len(picked) >= n:
                break
            before = len(picked)
            take([d for d in docs if d["source"] == src], 1, "random-fill")
            added += len(picked) - before
        if added == 0:
            break  # pool exhausted

    rng.shuffle(picked)  # randomise annotation order
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["position", "document_id", "url", "source", "event_type", "stratum"])
        for pos, did in enumerate(picked, 1):
            d = by_id[did]
            w.writerow([pos, did, d["url"], d["source"], d.get("event_type") or "",
                        d.get("_stratum", "")])
    return CSV_PATH


def load_ids() -> list[int]:
    """Ordered current-DB document ids for the frozen sample (matched by URL).

    Returns [] if the sample has not been built yet.
    """
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    urls = [r["url"] for r in rows]
    with db.get_conn() as conn:
        url_to_id = {r["url"]: r["id"] for r in conn.execute(
            "SELECT id, url FROM documents WHERE url != ''").fetchall()}
    return [url_to_id[u] for u in urls if u in url_to_id]


def summary() -> dict:
    if not CSV_PATH.exists():
        return {"built": False}
    with CSV_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    from collections import Counter
    return {"built": True, "n": len(rows),
            "by_source": dict(Counter(r["source"] for r in rows)),
            "by_stratum": dict(Counter(r["stratum"] for r in rows))}


if __name__ == "__main__":
    import json
    path = build()
    print("wrote", path)
    print(json.dumps(summary(), indent=2))
