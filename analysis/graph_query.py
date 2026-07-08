"""
Knowledge-graph queries (Phase 3): answer multi-hop questions automatically.

The headline capability: instead of manually reading papers, ask the graph
questions like

    "Which countries have recently reported <linezolid> resistance?"
    "Which countries newly show <NDM>?"

We resolve these from document-level entity co-occurrence: find documents that
mention the focus entity, then aggregate the countries (or any target type) they
co-occur with, split into recent vs earlier so "new" appearances stand out.

This is graph/relational reasoning, not keyword search. Roadmap: add embedding
similarity so the focus term can be fuzzy/semantic rather than exact.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import db
from extract.dictionaries import canonical_country

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def connected(focus_type: str, focus_value: str, target_type: str = "country",
              recent_days: int = 90) -> pd.DataFrame:
    """
    Entities of `target_type` co-occurring with (focus_type=focus_value) in the
    same document. Returns total docs, recent docs, and a 'new' flag (present
    only in the recent window, never before).
    """
    cutoff = (date.today() - timedelta(days=recent_days)).isoformat()
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT t.value AS value, {DATE_EXPR} AS day, d.id AS did
                FROM documents d
                JOIN entities f ON f.document_id = d.id
                     AND f.entity_type = ? AND f.value = ?
                JOIN entities t ON t.document_id = d.id AND t.entity_type = ?
                """,
            (focus_type, focus_value, target_type),
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["value", "total_docs", "recent_docs", "status"])
    df = pd.DataFrame([dict(r) for r in rows])
    if target_type == "country":
        df["value"] = df["value"].map(canonical_country)
    df["is_recent"] = df["day"] >= cutoff
    recent = df[df["is_recent"]].groupby("value")["did"].nunique()
    earlier = df[~df["is_recent"]].groupby("value")["did"].nunique()
    out = pd.DataFrame({"recent_docs": recent, "earlier_docs": earlier}).fillna(0).astype(int)
    out["total_docs"] = out["recent_docs"] + out["earlier_docs"]
    out["status"] = out.apply(
        lambda r: "🆕 new" if (r["earlier_docs"] == 0 and r["recent_docs"] > 0)
        else ("active" if r["recent_docs"] > 0 else "historical"), axis=1)
    out = out.sort_values(["status", "recent_docs", "total_docs"],
                          ascending=[True, False, False])
    return out.reset_index().rename(columns={"index": "value"})[
        ["value", "total_docs", "recent_docs", "earlier_docs", "status"]]


def example_documents(focus_type: str, focus_value: str, target_type: str,
                      target_value: str, limit: int = 5) -> list[dict]:
    """Documents where the focus and target entities co-occur (evidence)."""
    tv = target_value
    with db.get_conn() as conn:
        # match either the raw or canonical country name
        rows = conn.execute(
            f"""SELECT DISTINCT d.title, d.url, d.source, {DATE_EXPR} AS day
                FROM documents d
                JOIN entities f ON f.document_id=d.id AND f.entity_type=? AND f.value=?
                JOIN entities t ON t.document_id=d.id AND t.entity_type=?
                WHERE t.value = ? OR t.value = ?
                ORDER BY day DESC LIMIT ?""",
            (focus_type, focus_value, target_type, tv, tv, limit),
        ).fetchall()
    return [dict(r) for r in rows]
