"""
Risk page (Phase 4) — country AMR risk signal, shown WITH its validation.

Deliberately shows the risk score next to the evidence of how much to trust it
(construct validity against WHO GHO / GLASS resistance data, and surge-task
backtest skill). No unvalidated number stands alone.
"""
import sys
from pathlib import Path

import altair as alt
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
from analysis import risk  # noqa: E402

page_setup("Risk", "⚠️")
st.title("⚠️ Country AMR Risk — with validation")
st.caption("A risk signal is only as good as its validation. This page shows the "
           "score and, right beside it, how well it tracks real resistance data.")

recent_days = st.slider("Signal window (days)", 30, 120, 60)

# --- 1. validation first (set expectations before showing the score) ---------
st.subheader("① Does the signal track reality? (construct validity)")
cv = risk.construct_validity(recent_days=max(recent_days, 90))
if not cv.get("ok"):
    st.info(f"Not enough overlapping data yet: {cv.get('reason')}")
else:
    a, b, c = st.columns(3)
    a.metric("Countries compared", cv["n"])
    b.metric("Spearman ρ — raw volume", cv["spearman_volume"],
             "reporting bias" if abs(cv["spearman_volume"]) < 0.15 else "")
    c.metric("Spearman ρ — AMR share", cv["spearman_share"],
             "normalisation helps" if cv["spearman_share"] > cv["spearman_volume"] else "")
    st.caption("vs WHO GHO / GLASS measured resistance (% MRSA bloodstream infections). "
               "Raw document volume mostly reflects who publishes; the normalised "
               "AMR *share* is the fairer signal.")
    pairs = cv["pairs"]
    chart = (alt.Chart(pairs).mark_circle(size=90, opacity=0.7, color="#0b7285")
             .encode(x=alt.X("gho_resistance_%:Q", title="WHO GHO measured resistance (%)"),
                     y=alt.Y("amr_share:Q", title="platform AMR share"),
                     tooltip=["country", "amr_share", "gho_resistance_%"]))
    text = chart.mark_text(dy=-10, fontSize=10).encode(text="country")
    st.altair_chart((chart + text).properties(height=340), use_container_width=True)

st.divider()

# --- 2. the risk signal (now the reader knows how much to trust it) ----------
st.subheader("② Country risk signal")
st.caption("Composite percentile of recent AMR document volume + velocity. "
           "A **signal index**, not a validated probability — read together with ①.")
cr = risk.country_risk(recent_days=recent_days)
if cr.empty:
    st.info("Not enough data yet.")
else:
    show = cr[["country", "total_docs", "recent_amr", "velocity", "risk_signal"]].head(20)
    st.dataframe(show, hide_index=True, use_container_width=True,
                 column_config={"risk_signal": st.column_config.ProgressColumn(
                     "risk signal", min_value=0, max_value=100, format="%d")})
    st.warning("⚠️ Reporting-bias caveat: countries with large research output "
               "(e.g. the United States) rank high partly because they publish more, "
               "not necessarily because risk is higher. This is exactly why ① matters "
               "and why the roadmap normalises per baseline volume and per capita.")

st.divider()

# --- 3. predictive skill for the self-contained surge task -------------------
st.subheader("③ Predictive skill (surge task backtest)")
sk = risk.surge_skill()
if not sk.get("ok"):
    st.info("Not enough history to backtest yet.")
else:
    d1, d2, d3 = st.columns(3)
    d1.metric("Pathogens tested", sk["n_pathogens"])
    d2.metric("Model MAE", sk["mean_linear_mae"])
    d3.metric("Naive MAE", sk["mean_naive_mae"],
              "model wins" if sk["beats_naive"] else "not yet beating naive",
              delta_color="normal" if sk["beats_naive"] else "off")
    if not sk["beats_naive"]:
        st.caption("Honest status: on today's small dataset the model does not yet beat "
                   "the naive baseline — expected, and it improves as history accumulates. "
                   "Reporting this (rather than hiding it) is the point.")

st.info(
    "**Methodology (transparent by design).** Ground truth = WHO GHO / GLASS "
    "resistance indicators (fetched automatically, 101 countries, 2016–2023). "
    "The score is validated, not asserted: construct validity now, temporal "
    "prediction as multi-year history accumulates. Roadmap: logistic/Poisson "
    "model predicting next-period resistance change, AUROC/AUPRC + calibration + "
    "decision-curve analysis, reporting-bias adjustment, and income-stratified "
    "and leave-one-source-out sensitivity analyses.",
    icon="🧪",
)
