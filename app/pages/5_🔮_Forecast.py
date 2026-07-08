"""
Forecast page — a minimal, transparent prediction prototype.

Forecasts the next N weeks of "discussion volume" for a chosen pathogen using an
OLS linear-trend baseline, with a prediction band and a rolling backtest that
compares the model against naive baselines. Honestly labelled as early-stage.
"""
import sys
from pathlib import Path

import altair as alt
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup, get_top, distinct_values  # noqa: E402
from analysis import forecast as fc  # noqa: E402

page_setup("Forecast", "🔮")
st.title("🔮 Discussion-volume forecast")
st.caption("Predicts the next few weeks of how much a pathogen is discussed across "
           "the collected sources. Transparent baseline model — not a black box.")

c1, c2, c3 = st.columns([2, 1, 1])
options = distinct_values("pathogen")
top = [r["value"] for r in get_top("pathogen", 3650, 8).to_dict("records")]
default = next((p for p in ["CRE", "MRSA"] + top if p in options), options[0] if options else None)
with c1:
    pathogen = st.selectbox("Pathogen", options,
                            index=options.index(default) if default in options else 0) if options else None
with c2:
    horizon = st.slider("Weeks ahead", 2, 8, 4)
with c3:
    window = st.slider("History window (weeks)", 8, 52, 26)

if not pathogen:
    st.info("No data yet. Run `python run_daily.py` first.")
    st.stop()

result = fc.forecast("pathogen", pathogen, horizon=horizon, weeks=window)

if not result["ok"]:
    st.warning(result["reason"])
    st.stop()

# --- headline metrics --------------------------------------------------------
m1, m2, m3 = st.columns(3)
arrow = {"rising": "↗", "declining": "↘", "flat": "→"}[result["direction"]]
m1.metric("Trend", f"{arrow} {result['direction']}", f"{result['slope_per_week']:+.2f}/week")
next_mean = result["forecast"]["mean"][0]
m2.metric(f"Next week (predicted)", f"{next_mean:.1f} docs")
ev = result.get("evaluation") or {}
if ev:
    beats = ev.get("linear_mae", 9) <= min(ev.get("naive_mae", 9), ev.get("movavg_mae", 9))
    m3.metric("Backtest MAE (model)", ev.get("linear_mae", "—"),
              "beats naive" if beats else "≈ naive", delta_color="normal" if beats else "off")

# --- chart: history + forecast + prediction band -----------------------------
frame = fc.forecast_frame(result)
band = frame[frame["kind"] == "forecast"]

base = alt.Chart(frame)
actual = (base.transform_filter(alt.datum.kind == "actual")
          .mark_line(point=True, color="#0b7285")
          .encode(x=alt.X("week:T", title=None), y=alt.Y("value:Q", title="documents / week")))
fc_line = (base.transform_filter(alt.datum.kind == "forecast")
           .mark_line(point=True, strokeDash=[6, 4], color="#e8590c")
           .encode(x="week:T", y="value:Q"))
band_area = (alt.Chart(band).mark_area(opacity=0.18, color="#e8590c")
             .encode(x="week:T", y=alt.Y("lo:Q", title=None), y2="hi:Q"))
st.altair_chart((band_area + actual + fc_line).properties(height=340),
                use_container_width=True)
st.caption("Blue = actual weekly counts · Orange dashed = forecast · Shaded = 95% prediction band")

# --- honest evaluation table -------------------------------------------------
st.subheader("How good is it? (rolling backtest)")
if ev:
    st.write(f"Held out the last **{horizon} weeks** and measured mean absolute error (MAE) — "
             "lower is better. A model worth using should beat the naive baselines:")
    st.dataframe({
        "method": ["Linear trend (this model)", "Naive (last value)", "4-week moving average"],
        "MAE (docs)": [ev.get("linear_mae"), ev.get("naive_mae"), ev.get("movavg_mae")],
    }, hide_index=True, use_container_width=True)
else:
    st.info("Not enough weeks yet to run a backtest — it activates once there is more history.")

st.info(
    "**This is an early-stage prototype (Paper 2 direction).** Model = ordinary "
    "least-squares linear trend on weekly counts — a deliberately simple, "
    "transparent baseline. On today's small dataset the signal is limited and "
    "the model roughly ties the naive baseline; accuracy improves as the platform "
    "accumulates weeks of data. Roadmap: ARIMA / Prophet / Poisson models and "
    "true early-warning lead-time evaluation against GLASS.",
    icon="🧪",
)
