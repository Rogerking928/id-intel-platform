"""Trends page — AI narrative + time-series charts."""
import sys
from pathlib import Path

import altair as alt
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup, get_top, get_rising, get_timeseries, distinct_values  # noqa: E402
from analysis import trends  # noqa: E402

page_setup("Trends", "📈")
st.title("📈 AI Trend Analysis")

days = st.slider("Analysis window (days)", 14, 180, 30, step=7)

with st.spinner("Computing trends…"):
    facts = trends.build_trend_facts(days=days)

st.subheader("🧠 AI narrative")
with st.spinner("Writing analysis…"):
    st.write(trends.narrative(facts))
if not facts["overview"]["total"]:
    st.info("Populate the database first with `python run_daily.py`.")

st.divider()
st.subheader("Fastest rising")
c1, c2, c3 = st.columns(3)
for col, etype, label in [(c1, "pathogen", "Pathogens"),
                          (c2, "resistance_gene", "Resistance mechanisms"),
                          (c3, "antibiotic", "Antibiotics")]:
    with col:
        st.markdown(f"**{label}**")
        df = get_rising(etype, days)
        st.dataframe(df, hide_index=True, use_container_width=True) if not df.empty else st.write("_n/a_")

st.divider()
st.subheader("Trajectory over time (weekly document counts)")
etype = st.selectbox("Entity type", ["pathogen", "resistance_gene", "antibiotic", "country"])
options = distinct_values(etype)
default = [o["value"] for o in get_top(etype, days, 5).to_dict("records")] if options else []
picked = st.multiselect("Compare", options, default=[d for d in default if d in options][:5])
if picked:
    ts = get_timeseries(etype, tuple(picked), days=max(days, 120))
    if ts.empty:
        st.write("_Not enough dated data yet for a time series._")
    else:
        chart = (alt.Chart(ts).mark_line(point=True)
                 .encode(x=alt.X("week:T", title="week"),
                         y=alt.Y("documents:Q", title="documents"),
                         color=alt.Color("value:N", title=etype))
                 .properties(height=360))
        st.altair_chart(chart, use_container_width=True)
else:
    st.caption("Pick one or more values to plot their trajectory.")
