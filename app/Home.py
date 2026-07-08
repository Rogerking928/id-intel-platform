"""
ID-Intel dashboard — home page.

Run from the project root:   streamlit run app/Home.py
"""
import altair as alt
import streamlit as st

from common import (page_setup, get_overview, get_top, get_rising,
                    recent_documents, render_doc_card, latest_run)

page_setup("Dashboard")

st.title("🦠 Global AMR & Infectious Disease Intelligence")
st.caption("An AI platform that collects, extracts, and analyses open-source "
           "infectious-disease & antimicrobial-resistance information every day.")

run = latest_run()
if run:
    st.info(f"Last data update: {run['finished_at']} — {run['summary']}")
else:
    st.warning("No data yet. Run `python run_daily.py` first to populate the database.")

# --- top metrics -------------------------------------------------------------
ov = get_overview(30)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Documents (total)", ov["total"])
c2.metric("New in last 30 days", ov["recent"])
c3.metric("Sources", len(ov["by_source"]))
top_path = get_top("pathogen", 30, 1)
c4.metric("Top pathogen (30d)",
          top_path.iloc[0]["value"] if not top_path.empty else "—")

st.divider()

# --- Today / Highlights ------------------------------------------------------
left, right = st.columns(2)
with left:
    st.subheader("🔥 Today's ID highlights")
    df = recent_documents(days=3, event_types=("Outbreak", "Emerging Pathogen"), limit=6)
    if df.empty:
        df = recent_documents(days=14, event_types=("Outbreak", "Emerging Pathogen"), limit=6)
    if df.empty:
        st.write("_No recent outbreak items._")
    for _, r in df.iterrows():
        render_doc_card(r.to_dict())

with right:
    st.subheader("🧫 Today's AMR highlights")
    df = recent_documents(days=3,
                          event_types=("Antimicrobial Resistance", "New Drug"), limit=6)
    if df.empty:
        df = recent_documents(days=14,
                              event_types=("Antimicrobial Resistance", "New Drug"), limit=6)
    if df.empty:
        st.write("_No recent AMR items._")
    for _, r in df.iterrows():
        render_doc_card(r.to_dict())

st.divider()

# --- 30-day trend charts -----------------------------------------------------
st.subheader("📈 Last 30 days — what's being discussed")
tc1, tc2 = st.columns(2)


def bar(df, x, y, color):
    if df.empty:
        st.write("_No data yet._")
        return
    chart = (alt.Chart(df).mark_bar(color=color)
             .encode(x=alt.X(f"{x}:Q", title="documents"),
                     y=alt.Y(f"{y}:N", sort="-x", title=None))
             .properties(height=280))
    st.altair_chart(chart, use_container_width=True)


with tc1:
    st.markdown("**Top pathogens**")
    bar(get_top("pathogen", 30, 10), "documents", "value", "#0b7285")
    st.markdown("**Top resistance mechanisms**")
    bar(get_top("resistance_gene", 30, 10), "documents", "value", "#5f3dc4")
with tc2:
    st.markdown("**Most active countries**")
    bar(get_top("country", 30, 10), "documents", "value", "#e8590c")
    st.markdown("**Top antibiotics**")
    bar(get_top("antibiotic", 30, 10), "documents", "value", "#2b8a3e")

st.divider()

# --- fastest rising ----------------------------------------------------------
st.subheader("🚀 Fastest rising (last 30d vs previous 30d)")
rc1, rc2 = st.columns(2)
with rc1:
    st.markdown("**Pathogens**")
    rp = get_rising("pathogen", 30)
    st.dataframe(rp, hide_index=True, use_container_width=True) if not rp.empty else st.write("_n/a_")
with rc2:
    st.markdown("**Resistance mechanisms**")
    rg = get_rising("resistance_gene", 30)
    st.dataframe(rg, hide_index=True, use_container_width=True) if not rg.empty else st.write("_n/a_")

st.divider()

# --- latest by type ----------------------------------------------------------
st.subheader("🆕 Latest")
lp, lt, lg = st.columns(3)
with lp:
    st.markdown("**Publications**")
    for _, r in recent_documents(days=60, sources=("PubMed",), limit=6).iterrows():
        render_doc_card(r.to_dict())
with lt:
    st.markdown("**Clinical trials**")
    for _, r in recent_documents(days=120, sources=("ClinicalTrials",), limit=6).iterrows():
        render_doc_card(r.to_dict())
with lg:
    st.markdown("**Guidelines / alerts**")
    for _, r in recent_documents(days=120, event_types=("Guideline",), limit=6).iterrows():
        render_doc_card(r.to_dict())

st.caption("Pages in the sidebar → Search · Trends · Knowledge Graph · Weekly Report")
