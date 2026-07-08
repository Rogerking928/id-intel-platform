"""
Novelty page (Phase 4): new-knowledge discovery.

Surfaces entity combinations that appear in recent documents but have never
co-occurred earlier in the corpus — the "first time X + Y + Z" detector.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
from analysis import novelty  # noqa: E402

page_setup("Novelty", "🧬")
st.title("🧬 Novelty Detector")
st.caption("Not news aggregation — knowledge discovery. Flags combinations "
           "(resistance gene + pathogen + country) seen in recent documents but "
           "never together earlier in the corpus.")

recent_days = st.slider("Treat documents from the last N days as 'new'", 14, 90, 30)
findings = novelty.novel_findings(recent_days=recent_days, limit=60)

triples = [f for f in findings if f["size"] == 3]
pairs = [f for f in findings if f["size"] == 2]

st.metric("Novel combinations detected", len(findings),
          f"{len(triples)} three-way · {len(pairs)} two-way")

if triples:
    st.subheader("🧬 Novel three-way findings (gene + pathogen + country)")
    st.caption("The most specific — a resistance mechanism, an organism and a place "
               "reported together for the first time in the collected data.")
    for f in triples[:20]:
        st.markdown(
            f"<div style='padding:9px 12px;border-left:3px solid #b4232a;background:#fbecec;"
            f"border-radius:0 8px 8px 0;margin-bottom:7px'>"
            f"<b>🧬 {f['combination']}</b><br>"
            f"<span style='font-size:.8rem;color:#555'>{f['day']} · {f['source']} · "
            f"<a href='{f['url']}'>{(f['title'] or 'source')[:80]}</a></span></div>",
            unsafe_allow_html=True)

if pairs:
    st.subheader("New two-way combinations")
    st.dataframe(pd.DataFrame([{"combination": f["combination"], "date": f["day"],
                                "source": f["source"], "document": f["title"]}
                               for f in pairs[:30]]),
                 hide_index=True, use_container_width=True)

if not findings:
    st.info("No novel combinations at this window (or not enough data yet).")

st.info(
    "**Early-stage — the baseline matters.** With a young corpus almost everything "
    "looks novel because there is little history to compare against. As the platform "
    "accumulates months/years of documents, this becomes a genuine 'first report' "
    "detector. Roadmap: embedding-based semantic novelty (compare each new document "
    "against the full multi-year corpus) and a confidence score per finding.",
    icon="🧪",
)
