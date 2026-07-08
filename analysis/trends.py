"""
Trend analytics computed from the entities table (which reflects the active
extraction of each document).

All functions return plain Python structures / pandas DataFrames so both the
Streamlit dashboard and the weekly report can reuse them.

Dates: we use published_date when present, else fall back to fetched_at, so a
document always lands in a time bucket.
"""
from collections import Counter
from datetime import date, datetime, timedelta

import pandas as pd

import db


def _effective_date_expr() -> str:
    # substr(fetched_at,1,10) turns the ISO timestamp into a YYYY-MM-DD date.
    return "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def _entities_df(entity_type: str, days: int | None = None) -> pd.DataFrame:
    date_expr = _effective_date_expr()
    sql = f"""
        SELECT e.value AS value, {date_expr} AS day, d.source AS source, d.id AS doc_id
        FROM entities e JOIN documents d ON d.id = e.document_id
        WHERE e.entity_type = ?
    """
    params = [entity_type]
    if days is not None:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        sql += f" AND {date_expr} >= ?"
        params.append(cutoff)
    with db.get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def top_entities(entity_type: str, days: int = 30, limit: int = 15) -> pd.DataFrame:
    df = _entities_df(entity_type, days)
    if df.empty:
        return pd.DataFrame(columns=["value", "documents"])
    counts = (df.groupby("value")["doc_id"].nunique()
              .sort_values(ascending=False).head(limit))
    return counts.rename("documents").reset_index()


def fastest_rising(entity_type: str, window: int = 30, limit: int = 10) -> pd.DataFrame:
    """Compare the last `window` days against the `window` days before that."""
    df = _entities_df(entity_type, days=window * 2)
    if df.empty:
        return pd.DataFrame(columns=["value", "recent", "previous", "change"])
    today = date.today()
    split = (today - timedelta(days=window)).isoformat()
    df["recent"] = df["day"] >= split
    recent = df[df["recent"]].groupby("value")["doc_id"].nunique()
    previous = df[~df["recent"]].groupby("value")["doc_id"].nunique()
    out = pd.DataFrame({"recent": recent, "previous": previous}).fillna(0).astype(int)
    out["change"] = out["recent"] - out["previous"]
    out = out.sort_values(["change", "recent"], ascending=False).head(limit)
    return out.reset_index().rename(columns={"index": "value"})


def timeseries(entity_type: str, values: list[str], days: int = 90) -> pd.DataFrame:
    """Weekly document counts per value, for line charts."""
    df = _entities_df(entity_type, days)
    if df.empty:
        return pd.DataFrame(columns=["week", "value", "documents"])
    df = df[df["value"].isin(values)].copy()
    if df.empty:
        return pd.DataFrame(columns=["week", "value", "documents"])
    df["week"] = pd.to_datetime(df["day"], errors="coerce").dt.to_period("W").dt.start_time
    grp = (df.dropna(subset=["week"]).groupby(["week", "value"])["doc_id"]
           .nunique().rename("documents").reset_index())
    return grp


def country_signals(days: int = 30, limit: int = 12) -> pd.DataFrame:
    return top_entities("country", days=days, limit=limit)


def overview_counts(days: int = 30) -> dict:
    with db.get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
        date_expr = _effective_date_expr()
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        recent = conn.execute(
            f"SELECT COUNT(*) c FROM documents d WHERE {date_expr} >= ?", (cutoff,)
        ).fetchone()["c"]
        by_source = {r["source"]: r["c"] for r in conn.execute(
            "SELECT source, COUNT(*) c FROM documents GROUP BY source").fetchall()}
    return {"total": total, "recent": recent, "by_source": by_source, "window_days": days}


def build_trend_facts(days: int = 30) -> dict:
    """A compact dict of the key numbers, reused by the LLM narrative + report."""
    return {
        "window_days": days,
        "overview": overview_counts(days),
        "top_pathogens": top_entities("pathogen", days).to_dict("records"),
        "rising_pathogens": fastest_rising("pathogen", days).to_dict("records"),
        "top_genes": top_entities("resistance_gene", days).to_dict("records"),
        "rising_genes": fastest_rising("resistance_gene", days).to_dict("records"),
        "top_antibiotics": top_entities("antibiotic", days).to_dict("records"),
        "rising_antibiotics": fastest_rising("antibiotic", days).to_dict("records"),
        "top_countries": country_signals(days).to_dict("records"),
        "top_event_types": top_entities("event_type", days).to_dict("records"),
    }


# ---------------------------------------------------------------------------
# Narrative: LLM if a key is set, otherwise a solid templated summary.
# ---------------------------------------------------------------------------
def _template_narrative(facts: dict) -> str:
    d = facts["window_days"]
    ov = facts["overview"]
    lines = [f"In the last {d} days the platform ingested {ov['recent']} new documents "
             f"({ov['total']} total across all sources)."]

    def _fmt(records, label, key="documents"):
        if not records:
            return None
        top = ", ".join(f"{r['value']} ({r.get(key, r.get('recent',''))})" for r in records[:5])
        return f"Most-discussed {label}: {top}."

    for records, label in [
        (facts["top_pathogens"], "pathogens"),
        (facts["top_genes"], "resistance mechanisms"),
        (facts["top_antibiotics"], "antibiotics"),
        (facts["top_countries"], "countries"),
    ]:
        s = _fmt(records, label)
        if s:
            lines.append(s)

    rising = facts["rising_pathogens"]
    rising = [r for r in rising if r.get("change", 0) > 0]
    if rising:
        top = ", ".join(f"{r['value']} (+{r['change']})" for r in rising[:5])
        lines.append(f"Fastest-rising pathogens vs the previous {d} days: {top}.")
    rgenes = [r for r in facts["rising_genes"] if r.get("change", 0) > 0]
    if rgenes:
        top = ", ".join(f"{r['value']} (+{r['change']})" for r in rgenes[:5])
        lines.append(f"Resistance mechanisms gaining attention: {top}.")
    return " ".join(lines)


def narrative(facts: dict) -> str:
    """LLM-written analysis if Gemini is configured, else a templated narrative."""
    from extract import llm
    if not llm.is_available():
        return _template_narrative(facts)
    try:
        import json
        from collectors.base import _session
        import config
        prompt = (
            "You are an AMR & infectious-disease surveillance analyst. Based ONLY on "
            "these aggregate statistics from an open-source ID intelligence platform, "
            "write a concise 200-300 word trend analysis for ID clinicians: what is "
            "being discussed most, what is rising fastest, which regions/countries stand "
            "out, and 2-3 emerging research directions worth watching. Do not invent "
            "numbers beyond those given.\n\nSTATS JSON:\n" + json.dumps(facts, ensure_ascii=False)
        )
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{config.GEMINI_MODEL}:generateContent")
        resp = _session.post(url, params={"key": config.GEMINI_API_KEY},
                             json={"contents": [{"parts": [{"text": prompt}]}],
                                   "generationConfig": {"temperature": 0.3}},
                             timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:  # noqa: BLE001
        return _template_narrative(facts) + f"\n\n(LLM narrative unavailable: {exc})"
