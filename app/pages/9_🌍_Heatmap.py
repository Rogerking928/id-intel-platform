"""
AMR Heatmap page (Phase 4): a world map you read at a glance.

Colours each country by how many collected documents mention it, optionally
filtered to a specific pathogen or resistance mechanism — so you can see, e.g.,
where carbapenem-resistant organisms are being reported most.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup, distinct_values  # noqa: E402
import db  # noqa: E402
from extract.dictionaries import canonical_country  # noqa: E402

page_setup("Heatmap", "🌍")
st.title("🌍 Global AMR Heatmap")
st.caption("Where is it being reported? Countries coloured by document volume. "
           "Optionally focus on one pathogen or resistance mechanism.")

# plotly's "country names" locationmode needs a few of our names remapped
PLOTLY_FIX = {
    "United States": "United States of America",
    "Democratic Republic of the Congo": "Democratic Republic of the Congo",
    "Tanzania": "United Republic of Tanzania",
}

c1, c2 = st.columns([1.2, 1])
focus_kind = c1.selectbox("Focus on", ["All documents", "pathogen", "resistance_gene", "antibiotic"])
focus_value = None
if focus_kind != "All documents":
    vals = distinct_values(focus_kind)
    focus_value = c2.selectbox("Value", vals) if vals else None

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"
if focus_kind == "All documents":
    sql = """SELECT e.value AS country, COUNT(DISTINCT d.id) AS docs
             FROM entities e JOIN documents d ON d.id = e.document_id
             WHERE e.entity_type='country' GROUP BY e.value"""
    params = ()
else:
    sql = """SELECT c.value AS country, COUNT(DISTINCT d.id) AS docs
             FROM documents d
             JOIN entities c ON c.document_id=d.id AND c.entity_type='country'
             JOIN entities f ON f.document_id=d.id AND f.entity_type=? AND f.value=?
             GROUP BY c.value"""
    params = (focus_kind, focus_value)

with db.get_conn() as conn:
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

if not rows or (focus_value is None and focus_kind != "All documents"):
    st.info("Not enough geolocated data for this selection yet.")
    st.stop()

df = pd.DataFrame(rows)
df["country"] = df["country"].map(canonical_country)
df = df.groupby("country", as_index=False)["docs"].sum()
df["plot_name"] = df["country"].map(lambda c: PLOTLY_FIX.get(c, c))

title = "Document mentions by country" + (
    f" — {focus_value}" if focus_value else "")
fig = px.choropleth(
    df, locations="plot_name", locationmode="country names",
    color="docs", hover_name="country",
    color_continuous_scale="YlOrRd", labels={"docs": "documents"},
)
fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=460,
                  geo=dict(showframe=False, showcoastlines=True,
                           projection_type="natural earth"))
st.plotly_chart(fig, use_container_width=True)

st.markdown("#### Top countries")
st.dataframe(df.sort_values("docs", ascending=False).head(15)[["country", "docs"]],
             hide_index=True, use_container_width=True)

st.caption("Note: geolocation comes from country names detected in each document, "
           "so it reflects where topics are *reported/studied*, not confirmed case "
           "counts. Roadmap: weight by outbreak severity and normalise per capita.")
