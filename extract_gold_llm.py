"""Run the LLM extractor on exactly the frozen gold-sample documents.

The benchmark compares the LLM against the gold standard, so the LLM must have
processed the SAME documents you annotate. Gemini's free tier is rate-limited, so
this script is capped per run and resumable: run it on successive days (or raise
GEMINI_MAX_PER_RUN) until the gold set is fully covered.

Usage:
    python extract_gold_llm.py            # process up to GEMINI_MAX_PER_RUN docs
    python extract_gold_llm.py --cap 40   # override the per-run cap
"""
from __future__ import annotations

import argparse
import time

import config
import db
from analysis import gold_sample
from extract import llm


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cap", type=int, default=None, help="max docs this run")
    ap.add_argument("--interval", type=float, default=None, help="seconds between calls")
    args = ap.parse_args()

    if not llm.is_available():
        print("No GEMINI_API_KEY configured (.env). The rule-based baseline still "
              "works, but the LLM column of the benchmark needs a key.")
        return

    gold = gold_sample.load_ids()
    if not gold:
        print("No gold sample. Build it first:  python -m analysis.gold_sample")
        return

    name = llm.name()
    with db.get_conn() as conn:
        have = {r[0] for r in conn.execute(
            "SELECT document_id FROM extractions WHERE extractor=?", (name,)).fetchall()}
    todo = [i for i in gold if i not in have]
    cap = args.cap or config.GEMINI_MAX_PER_RUN or len(todo)
    interval = args.interval if args.interval is not None else config.GEMINI_MIN_INTERVAL
    print(f"gold={len(gold)}  already-LLM={len(gold) - len(todo)}  "
          f"pending={len(todo)}  this run={min(cap, len(todo))} (model {name})")

    consec_rl = 0
    for k, doc_id in enumerate(todo[:cap]):
        with db.get_conn() as conn:
            doc = dict(conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone())
        try:
            result, raw = llm.extract(doc["title"] or "", doc["raw_text"] or "", doc["source"])
            db.save_extraction(doc_id, name, name, config.PROMPT_VERSION,
                               result, raw_output=raw, make_active=True)
            db.rebuild_graph_for_document(doc_id)
            print(f"  [{k+1}/{min(cap, len(todo))}] doc {doc_id} ok")
            consec_rl = 0
        except Exception as exc:  # noqa: BLE001
            from analysis.trends import redact_secrets
            print(f"  [{k+1}] doc {doc_id} failed: {redact_secrets(str(exc))}")
            if "429" in str(exc) or "Too Many Requests" in str(exc):
                consec_rl += 1
                if consec_rl >= 3:
                    print("  rate-limited — stopping; resume tomorrow (quota resets).")
                    break
        if k < cap - 1 and interval > 0:
            time.sleep(interval)

    with db.get_conn() as conn:
        covered = len({r[0] for r in conn.execute(
            "SELECT document_id FROM extractions WHERE extractor=?", (name,)).fetchall()} & set(gold))
    print(f"gold LLM coverage now {covered}/{len(gold)}. "
          f"{'Complete.' if covered >= len(gold) else 'Re-run to continue.'}")


if __name__ == "__main__":
    main()
