"""
Outbreak page (Phase 4): live official-outbreak registry + honest validation.

Outcome = official alerts (WHO/CDC/ECDC/UKHSA); features = literature signal.
Source-separated so the validation isn't circular.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup  # noqa: E402
from analysis import outbreak  # noqa: E402

page_setup("Outbreak", "🌡️")
st.title("🌡️ Outbreak Watch")
st.caption("Official outbreaks being reported now, and an honest test of whether "
           "the platform's literature signal tracks them.")

recent_days = st.slider("'Active' window (days)", 21, 120, 45)

# --- live registry -----------------------------------------------------------
events = outbreak.active_outbreaks(recent_days=recent_days)
labels = outbreak.country_outbreak_labels(recent_days=recent_days)
c1, c2 = st.columns(2)
c1.metric("Official outbreak reports", len(events))
c2.metric("Countries affected", len(labels))

st.subheader("🚨 Currently reported (official sources)")
if not events:
    st.info("No official outbreak reports in this window.")
else:
    df = pd.DataFrame(events)
    for _, r in df.head(25).iterrows():
        st.markdown(f"- **[{(r['title'] or 'report')[:90]}]({r['url']})** — "
                    f"`{r['country']}` · {r['source']} · {r['day']}")

st.divider()

# --- source-separated validation --------------------------------------------
st.subheader("Does literature signal track official outbreaks?")
a = outbreak.association(recent_days=recent_days)
if not a.get("ok"):
    st.info(f"Not enough data yet: {a.get('reason')}")
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Countries analysed", a["n_countries"])
    auc = a["rank_auc"]
    m2.metric("Discrimination (rank-AUC)", auc,
              "no better than chance" if auc is not None and abs(auc - 0.5) < 0.1 else
              ("inverse!" if auc is not None and auc < 0.4 else "some signal"),
              delta_color="off")
    m3.metric("Mean lit signal (outbreak vs not)",
              f"{a['mean_signal_outbreak']} vs {a['mean_signal_no_outbreak']}")

    if auc is not None and auc < 0.45:
        st.warning(
            "**Key finding (and it's honest):** naive literature volume does **not** "
            "predict where official outbreaks occur — AUC is *below* 0.5, i.e. outbreaks "
            "cluster in **low-literature, low-resource countries** (e.g. DR Congo, Uganda) "
            "that are under-represented in the research stream. This is the **surveillance "
            "gap**, and quantifying it is itself a publishable result — it also tells us a "
            "useful early-warning model must NOT rely on raw literature volume.")
    st.dataframe(a["table"].head(20), hide_index=True, use_container_width=True)

st.info(
    "**Methodology.** Outcome = outbreaks officially reported by WHO DON / CDC / "
    "ECDC / UKHSA. Features = signal from a *different* source family (PubMed / "
    "preprints), so the test is not circular. Current design measures cross-sectional "
    "discrimination; the roadmap is a temporal early-warning model — does a signal "
    "rise PRECEDE the official alert, and by how many weeks (lead time vs GLASS/DON) — "
    "using outbreak-alert velocity and neighbouring-country spillover rather than raw "
    "publication counts.",
    icon="🧪",
)
