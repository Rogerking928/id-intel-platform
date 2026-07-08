"""
Daily pipeline — the one command that runs everything.

    python run_daily.py

Steps:
  1. init the database (safe to run repeatedly)
  2. collect from every source (WHO, CDC, ECDC, PubMed, ClinicalTrials, GLASS)
  3. store new documents
  4. run AI extraction + classification + knowledge-graph build
  5. (weekly) regenerate the weekly report

Schedule it daily with cron (Linux/WSL) or Task Scheduler (Windows).
See README for the exact cron line.
"""
import sys
import traceback
from datetime import date

import db
from collectors import pubmed, clinicaltrials, who, rss, glass, europepmc
from extract import pipeline

COLLECTORS = [
    ("WHO", who.collect),
    ("CDC", rss.collect_cdc),
    ("ECDC", rss.collect_ecdc),
    ("UKHSA", rss.collect_ukhsa),
    ("PubMed", pubmed.collect),
    ("Preprint", europepmc.collect),
    ("ClinicalTrials", clinicaltrials.collect),
    ("GLASS", glass.collect),
]


def collect_all() -> tuple[int, int]:
    total_new, total_seen = 0, 0
    for name, fn in COLLECTORS:
        print(f"[collect] {name} ...")
        try:
            docs = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  {name} crashed: {exc}")
            traceback.print_exc()
            continue
        new = 0
        for doc in docs:
            if not doc.get("source_id"):
                continue
            _id, is_new = db.upsert_document(doc)
            total_seen += 1
            if is_new:
                new += 1
        total_new += new
        print(f"  {name}: {len(docs)} fetched, {new} new")
    return total_new, total_seen


def main(make_report: bool = False):
    started = db.now_iso()
    print(f"=== ID-Intel daily run @ {started} ===")
    db.init_db()

    new, seen = collect_all()
    print(f"[collect] done: {new} new documents ({seen} seen)")

    # refresh the WHO GHO / GLASS AMR reference data (ground truth for risk scores)
    try:
        from collectors import gho
        print(f"[reference] WHO GHO AMR indicators: {gho.collect()} data points")
    except Exception as exc:  # noqa: BLE001
        print(f"  [reference] GHO refresh failed: {exc}")

    print("[extract] running AI extraction + classification + graph ...")
    stats = pipeline.run()

    summary = (f"collected new={new} seen={seen}; "
               f"extracted rule={stats['rule_based']} llm={stats['llm']} "
               f"(errors={stats['llm_errors']})")
    db.log_run(started, summary)

    if make_report or "--report" in sys.argv:
        from analysis import weekly_report
        out = weekly_report.generate()
        print(f"[report] weekly report -> {out['html']}")

    print(f"=== done: {summary} ===")


if __name__ == "__main__":
    main()
