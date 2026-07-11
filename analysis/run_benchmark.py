"""One-command Paper 1 benchmark report.

Scores every extractor (rule-based baseline, Gemini, ...) against a clinician's
gold annotations with per-field precision/recall/F1 and macro-F1, and — if a
second annotator has labelled the same gold documents — reports inter-annotator
Cohen's kappa. Writes a paper-ready report to reports/benchmark_<date>/.

Usage:
    python -m analysis.run_benchmark
    python -m analysis.run_benchmark --annotator "YHW" --second "Colleague"
"""
from __future__ import annotations

import argparse
from datetime import date

import config
import db
from analysis import benchmark, gold_sample


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotator", help="primary annotator name (default: first found)")
    ap.add_argument("--second", help="second annotator for kappa (default: second found)")
    args = ap.parse_args()

    annotators = db.list_annotators()
    if not annotators:
        print("No gold annotations yet. Label documents in the Streamlit "
              "'Annotate' page first, then re-run.")
        return
    primary = args.annotator or annotators[0]
    if primary not in annotators:
        print(f"Annotator '{primary}' has no annotations. Found: {annotators}")
        return

    with db.get_conn() as conn:
        extractors = [r[0] for r in conn.execute(
            "SELECT DISTINCT extractor FROM extractions ORDER BY extractor").fetchall()]

    table = benchmark.compare(primary, extractors)
    n_docs = table.attrs.get("n_docs", 0)
    gold_n = len(gold_sample.load_ids())

    out = [
        "# VIGIL Paper 1 — extraction benchmark",
        "",
        f"Primary annotator: **{primary}**",
        f"Scored documents (gold ∩ extracted): **{n_docs}**"
        f"  ·  frozen gold sample: {gold_n}  ·  annotators: {annotators}",
        "",
        "## Per-field F1 — extractor vs gold standard",
        "",
        "```",
        table.round(3).to_string(),
        "```",
    ]
    print("\n".join(out[5:]))

    second = args.second or (annotators[1] if len(annotators) > 1 else None)
    if second and second != primary and second in annotators:
        ia = benchmark.inter_annotator(primary, second)
        out += [
            "",
            f"## Inter-annotator agreement — {primary} vs {second} "
            f"(n = {ia.attrs.get('n_docs', 0)} shared documents)",
            "",
            "```",
            ia.to_string(index=False),
            "```",
            "",
            "_Cohen's κ is reported for single-label fields (event/study type); "
            "multi-label fields use micro-F1 agreement._",
        ]
        print("\n" + "\n".join(out[-6:]))
    else:
        out += ["", "> Inter-annotator κ pending: needs a **second annotator** on the "
                "same frozen gold documents."]
        print("\n(No second annotator yet — κ pending. Add one and re-run with --second.)")

    outdir = config.REPORTS_DIR / f"benchmark_{date.today().isoformat()}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "benchmark.md").write_text("\n".join(out), encoding="utf-8")
    table.round(3).to_csv(outdir / "per_field_f1.csv")
    print(f"\nWrote {outdir / 'benchmark.md'}")


if __name__ == "__main__":
    main()
