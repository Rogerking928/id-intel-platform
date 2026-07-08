"""Search page — filter all documents by pathogen, country, antibiotic, gene,
event type, source, disease, keyword and date."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import page_setup, distinct_values, render_doc_card  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import db  # noqa: E402

page_setup("Search", "🔎")
st.title("🔎 Search the knowledge base")

col = st.columns(4)
pathogen = col[0].selectbox("Pathogen", [""] + distinct_values("pathogen"))
country = col[1].selectbox("Country", [""] + distinct_values("country"))
antibiotic = col[2].selectbox("Antibiotic", [""] + distinct_values("antibiotic"))
gene = col[3].selectbox("Resistance gene", [""] + distinct_values("resistance_gene"))

col2 = st.columns(4)
disease = col2[0].selectbox("Disease", [""] + distinct_values("disease"))
event_type = col2[1].selectbox("Event type", [""] + distinct_values("event_type"))
source = col2[2].selectbox("Source", ["", "WHO", "CDC", "ECDC", "PubMed",
                                      "ClinicalTrials", "GLASS"])
days = col2[3].slider("Within last N days", 7, 365, 90)

text = st.text_input("Free-text (matches title/summary)", "")

# Build a query. Each entity filter is an EXISTS against the entities table.
DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"
sql = f"""
    SELECT DISTINCT d.id, d.title, d.url, d.source, {DATE_EXPR} AS day,
           e.event_type, e.summary
    FROM documents d
    LEFT JOIN extractions e ON e.document_id = d.id AND e.is_active = 1
    WHERE {DATE_EXPR} >= ?
"""
params = [(date.today() - timedelta(days=days)).isoformat()]


def add_entity_filter(etype, value):
    global sql
    if value:
        sql += (" AND EXISTS (SELECT 1 FROM entities x WHERE x.document_id=d.id "
                "AND x.entity_type=? AND x.value=?)")
        params.extend([etype, value])


add_entity_filter("pathogen", pathogen)
add_entity_filter("country", country)
add_entity_filter("antibiotic", antibiotic)
add_entity_filter("resistance_gene", gene)
add_entity_filter("disease", disease)
if event_type:
    sql += " AND e.event_type = ?"
    params.append(event_type)
if source:
    sql += " AND d.source = ?"
    params.append(source)
if text.strip():
    sql += " AND (d.title LIKE ? OR e.summary LIKE ?)"
    params.extend([f"%{text.strip()}%", f"%{text.strip()}%"])
sql += " ORDER BY day DESC LIMIT 200"

with db.get_conn() as conn:
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

st.markdown(f"### {len(rows)} result(s)")
if rows:
    st.download_button("⬇️ Download results as CSV",
                       pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
                       "search_results.csv", "text/csv")
for r in rows:
    render_doc_card(r)
    st.divider()
