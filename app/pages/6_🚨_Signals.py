"""
Signals page (Phase 2 intelligence): Growth Rate + Emerging Signal detection.

Goes beyond "who has the most documents" to "who is rising fastest" and "what
was quiet and just spiked" — the first real intelligence layer.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
from analysis import signals  # noqa: E402

page_setup("Signals", "🚨")
st.title("🚨 Trend Signals")
st.caption("Not just counts — growth rate and emerging signals. This is where the "
           "platform starts producing intelligence rather than tables.")

# --- Growth rate -------------------------------------------------------------
st.subheader("📈 Growth rate — who is rising fastest")
c1, c2 = st.columns([1, 1])
etype = c1.selectbox("Entity", ["pathogen", "resistance_gene", "antibiotic", "country"])
period = c2.slider("Period length (days)", 14, 90, 30,
                   help="Compares the most recent period against the preceding one.")
g = signals.growth_rate(etype, period_days=period, min_recent=1)
if g.empty:
    st.info("Not enough data in this window yet.")
else:
    st.caption(f"`recent` = last {period} days · `previous` = the {period} days before that · "
               "`NEW` = no prior activity")
    st.dataframe(g, hide_index=True, use_container_width=True)

st.divider()

# --- Emerging signals --------------------------------------------------------
st.subheader("🚨 Emerging signals — quiet before, loud now")
st.caption("Entities that were near-absent in the baseline window and then spiked. "
           "🚨 EMERGING = no baseline activity at all; ▲ surge = well above its own baseline rate.")
cc1, cc2 = st.columns(2)
ratio = cc1.slider("Sensitivity (recent ÷ baseline ≥)", 2.0, 6.0, 3.0, 0.5)
minrec = cc2.slider("Minimum recent documents", 1, 5, 2)
sig = signals.emerging_signals(min_recent=minrec, ratio=ratio)
if sig.empty:
    st.info("No emerging signals at this sensitivity.")
else:
    emerging = sig[sig["signal"].str.contains("EMERGING")]
    if not emerging.empty:
        st.markdown("**Brand-new signals (no prior activity):**")
        st.markdown(" ".join(
            f"<span style='background:#f8e3e3;color:#b4232a;padding:3px 9px;border-radius:8px;"
            f"margin:2px;display:inline-block;font-size:.85rem'>🚨 {r['value']} "
            f"<b>({r['type']})</b></span>"
            for _, r in emerging.head(12).iterrows()), unsafe_allow_html=True)
        st.write("")
    st.dataframe(sig, hide_index=True, use_container_width=True)

st.info(
    "**Early-stage — read as directional.** On a young dataset the baseline window "
    "is short, so many items look 'emerging' simply because history is thin. As the "
    "platform runs daily and accumulates months of data, the baseline stabilises and "
    "these signals become genuine early warnings. Roadmap: statistical significance "
    "testing (Poisson/EWMA control charts) and a novelty detector comparing each day "
    "against the full multi-year corpus.",
    icon="🧪",
)
