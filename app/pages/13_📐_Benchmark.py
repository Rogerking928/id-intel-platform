"""
Benchmark page (Paper 1) — score extractors against the gold standard.

Per-field precision/recall/F1 and macro-F1 for the rule-based baseline vs Gemini
(and any other stored extractor), plus inter-annotator agreement (κ / F1) and a
gold-standard export. This is the core Paper 1 result table.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
import db  # noqa: E402
from analysis import benchmark as bm  # noqa: E402

page_setup("Benchmark", "📐")
st.title("📐 Extraction Benchmark (Paper 1)")
st.caption("Scores each extractor against your clinician gold standard. "
           "Annotate documents on the ✍️ Annotate page first.")

annotators = db.list_annotators()
if not annotators:
    st.info("No annotations yet. Go to the ✍️ Annotate page and label some documents.")
    st.stop()

annotator = st.selectbox("Gold standard (annotator)", annotators)

# available extractors
with db.get_conn() as conn:
    extractors = [r["extractor"] for r in conn.execute(
        "SELECT DISTINCT extractor FROM extractions ORDER BY extractor").fetchall()]

st.subheader("Per-field F1 vs gold standard")
table = bm.compare(annotator, extractors)
if table.empty:
    st.info("No overlap between annotated documents and extractor outputs yet.")
else:
    st.caption(f"Evaluated on **{table.attrs.get('n_docs', 0)}** annotated documents "
               f"that also have extractions.")
    st.dataframe(table.round(3), use_container_width=True)
    st.caption("Rows = fields; last row = macro-F1. Columns = extractors "
               "(e.g. rule_based vs gemini-2.5-flash). Higher is better.")

st.divider()

# detailed P/R/F1 for one extractor
st.subheader("Detailed precision / recall / F1")
ex = st.selectbox("Extractor", extractors)
s = bm.score(annotator, ex)
st.metric("Macro-F1", s["macro_f1"], help=f"mean F1 across fields, n={s['n_docs']} docs")
st.dataframe(s["per_field"], hide_index=True, use_container_width=True)

st.divider()

# inter-annotator agreement
st.subheader("Inter-annotator agreement (κ / F1)")
if len(annotators) < 2:
    st.info("Add a second annotator (double-annotate ≥20% of documents) to compute "
            "reliability. Single-label fields report Cohen's κ; multi-label report F1.")
else:
    cc1, cc2 = st.columns(2)
    a1 = cc1.selectbox("Annotator A", annotators, index=0)
    a2 = cc2.selectbox("Annotator B", annotators, index=1)
    iaa = bm.inter_annotator(a1, a2)
    st.caption(f"On {iaa.attrs.get('n_docs', 0)} doubly-annotated documents. "
               "Target κ/F1 ≥ 0.6 (substantial).")
    st.dataframe(iaa, hide_index=True, use_container_width=True)

st.divider()

# export
st.subheader("Export gold standard")
gold = bm.export_gold(annotator)
st.download_button("⬇️ Download gold standard (CSV)",
                   gold.to_csv(index=False).encode("utf-8"),
                   f"gold_standard_{annotator}.csv", "text/csv")
st.caption(f"{len(gold)} annotated documents.")
