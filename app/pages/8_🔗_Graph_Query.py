"""
Graph Query page (Phase 3): ask the knowledge graph multi-hop questions.

e.g. "Which countries have recently reported linezolid / NDM / CRE?" — answered
automatically from entity co-occurrence, with 🆕 new-appearance flags and the
evidence documents behind each answer.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup, distinct_values  # noqa: E402
from analysis import graph_query as gq  # noqa: E402

page_setup("Graph Query", "🔗")
st.title("🔗 Knowledge-Graph Query")
st.caption("Ask the graph a question instead of reading papers by hand. "
           "Answers come from entity co-occurrence across documents.")

TYPES = ["resistance_gene", "antibiotic", "pathogen"]
c1, c2, c3 = st.columns([1, 1.4, 1])
focus_type = c1.selectbox("Focus", TYPES,
                          format_func=lambda t: t.replace("_", " "))
values = distinct_values(focus_type)
focus_value = c2.selectbox("Value", values) if values else None
recent_days = c3.slider("'Recent' window (days)", 30, 180, 90)

target_type = st.radio("Show connected", ["country", "antibiotic", "resistance_gene", "pathogen"],
                       horizontal=True, index=0)

if not focus_value:
    st.info("No data yet.")
    st.stop()

st.markdown(f"### {target_type.replace('_',' ').title()} connected to "
            f"**{focus_value}** _({focus_type.replace('_',' ')})_")

df = gq.connected(focus_type, focus_value, target_type, recent_days=recent_days)
if df.empty:
    st.info("No connections found for this entity.")
    st.stop()

new_ones = df[df["status"] == "🆕 new"]["value"].tolist()
if new_ones and target_type == "country":
    st.success(f"🆕 **Newly appearing:** {', '.join(new_ones)} "
               f"(seen only in the last {recent_days} days)")

st.dataframe(df, hide_index=True, use_container_width=True)

# evidence
st.divider()
pick = st.selectbox(f"Show evidence documents for a {target_type}", df["value"].tolist())
if pick:
    docs = gq.example_documents(focus_type, focus_value, target_type, pick)
    if not docs:
        st.write("_No documents found._")
    for d in docs:
        st.markdown(f"- **[{(d['title'] or 'source')[:90]}]({d['url']})** "
                    f"— {d['source']}, {d['day']}")

st.caption("Roadmap: add embedding similarity so the focus term can be fuzzy "
           "(e.g. any oxazolidinone, not just exact 'linezolid').")
