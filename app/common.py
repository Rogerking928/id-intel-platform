"""Shared helpers for the Streamlit pages (path setup + cached queries)."""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the project root importable when Streamlit runs a page file directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# On Streamlit Community Cloud there is no .env file; keys are provided via the
# app's "Secrets" box (st.secrets). Bridge them into the environment BEFORE
# importing config, so the Gemini key (if you add one) is picked up. Everything
# still works with no key at all — the LLM narrative just falls back to a
# template.
try:
    for _k in ("GEMINI_API_KEY", "GEMINI_MODEL", "NCBI_API_KEY"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass  # no secrets configured — fine

import db  # noqa: E402
from analysis import trends  # noqa: E402

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def page_setup(title: str, icon: str = "🦠"):
    st.set_page_config(page_title=f"VIGIL · {title}", page_icon=icon, layout="wide")


@st.cache_data(ttl=300)
def get_overview(days: int = 30) -> dict:
    return trends.overview_counts(days)


@st.cache_data(ttl=300)
def get_top(entity_type: str, days: int, limit: int = 15) -> pd.DataFrame:
    return trends.top_entities(entity_type, days=days, limit=limit)


@st.cache_data(ttl=300)
def get_rising(entity_type: str, window: int = 30, limit: int = 10) -> pd.DataFrame:
    return trends.fastest_rising(entity_type, window=window, limit=limit)


@st.cache_data(ttl=300)
def get_timeseries(entity_type: str, values: tuple, days: int = 120) -> pd.DataFrame:
    return trends.timeseries(entity_type, list(values), days=days)


@st.cache_data(ttl=120)
def recent_documents(days: int = 7, event_types: tuple = (), sources: tuple = (),
                     limit: int = 30) -> pd.DataFrame:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    sql = f"""
        SELECT d.id, d.title, d.url, d.source, {DATE_EXPR} AS day,
               e.event_type, e.summary, e.pathogens, e.countries,
               e.resistance_genes, e.antibiotics, e.study_type
        FROM documents d
        LEFT JOIN extractions e ON e.document_id = d.id AND e.is_active = 1
        WHERE {DATE_EXPR} >= ?
    """
    params = [cutoff]
    if event_types:
        sql += f" AND e.event_type IN ({','.join('?'*len(event_types))})"
        params += list(event_types)
    if sources:
        sql += f" AND d.source IN ({','.join('?'*len(sources))})"
        params += list(sources)
    sql += " ORDER BY day DESC LIMIT ?"
    params.append(limit)
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return pd.DataFrame(rows)


@st.cache_data(ttl=120)
def distinct_values(entity_type: str) -> list[str]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT value FROM entities WHERE entity_type=? ORDER BY value",
            (entity_type,),
        ).fetchall()
    return [r["value"] for r in rows]


@st.cache_data(ttl=120)
def latest_run() -> dict | None:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM run_log ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def render_doc_card(row: dict):
    title = row.get("title") or "Untitled"
    url = row.get("url") or "#"
    meta = f"{row.get('source','')} · {row.get('day','')} · {row.get('event_type') or 'n/a'}"
    st.markdown(f"**[{title}]({url})**  \n<span style='color:#888'>{meta}</span>",
                unsafe_allow_html=True)
    summary = row.get("summary")
    if summary:
        st.caption(summary[:400] + ("…" if len(summary) > 400 else ""))
