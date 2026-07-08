"""
Knowledge Graph page.

Pick a pathogen and see everything connected to it in the data:
Pathogen -> Country -> Resistance gene -> Antibiotic -> Disease, plus the
documents behind each link. Backed by the relations table in PostgreSQL-style
SQL (here SQLite); a real Neo4j graph is a later upgrade.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common import page_setup, distinct_values  # noqa: E402
import db  # noqa: E402

page_setup("Knowledge Graph", "🕸️")
st.title("🕸️ Knowledge Graph")
st.caption("Relationships mined from co-occurrence within documents. "
           "Pathogen → Country → Resistance gene → Antibiotic → Disease.")

pathogens = distinct_values("pathogen")
if not pathogens:
    st.info("No data yet. Run `python run_daily.py` first.")
    st.stop()

pathogen = st.selectbox("Pick a pathogen", pathogens)

LABELS = {
    "country": "🌍 Countries",
    "resistance_gene": "🧬 Resistance mechanisms",
    "antibiotic": "💊 Antibiotics",
    "disease": "🩺 Diseases / syndromes",
    "region": "🗺️ Regions",
}

with db.get_conn() as conn:
    cols = st.columns(len(LABELS))
    for col, (dst_type, label) in zip(cols, LABELS.items()):
        with col:
            st.markdown(f"**{label}**")
            rows = conn.execute(
                """SELECT dst_value AS value, COUNT(DISTINCT document_id) AS docs
                   FROM relations
                   WHERE src_type='pathogen' AND src_value=? AND dst_type=?
                   GROUP BY dst_value ORDER BY docs DESC LIMIT 15""",
                (pathogen, dst_type),
            ).fetchall()
            if rows:
                for r in rows:
                    st.write(f"- {r['value']}  ·  _{r['docs']}_")
            else:
                st.write("_none_")

st.divider()

# Build a readable "path" example like  CRE → Taiwan → NDM → Cefiderocol
st.subheader("Example knowledge paths")
with db.get_conn() as conn:
    example_docs = conn.execute(
        """SELECT DISTINCT d.id, d.title, d.url, d.source
           FROM documents d JOIN entities e ON e.document_id=d.id
           WHERE e.entity_type='pathogen' AND e.value=? LIMIT 25""",
        (pathogen,),
    ).fetchall()

    for d in example_docs[:12]:
        ents = conn.execute(
            "SELECT entity_type, value FROM entities WHERE document_id=?", (d["id"],)
        ).fetchall()
        buckets = {}
        for e in ents:
            buckets.setdefault(e["entity_type"], []).append(e["value"])
        chain = [pathogen]
        for t in ("country", "resistance_gene", "antibiotic", "disease"):
            if buckets.get(t):
                chain.append(buckets[t][0])
        if len(chain) > 1:
            st.markdown(
                "  →  ".join(f"`{c}`" for c in chain)
                + f"  ·  [{d['source']}]({d['url']}) — {(d['title'] or '')[:80]}"
            )
