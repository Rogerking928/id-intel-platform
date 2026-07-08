"""
Outbreak task (Phase 4) — detection + source-separated validation.

Design that avoids circularity:
  * OUTCOME (ground truth) = an outbreak officially reported by an alert body
    (WHO DON / CDC / ECDC / UKHSA), classified event_type='Outbreak'.
  * FEATURES = signal derived from the LITERATURE stream (PubMed / preprints)
    only — a different source family, so the features don't trivially contain
    the outcome.

Delivers now:
  1. active_outbreaks()  — a clean "what's officially being reported" registry.
  2. association()        — does literature signal for a country discriminate
     which countries have an official outbreak? (rank-AUC). Honest small-N.

The full temporal early-warning model (does literature rise PRECEDE the official
alert, and by how many weeks?) activates as history accumulates.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import db
from extract.dictionaries import canonical_country

OFFICIAL = ("WHO", "CDC", "ECDC", "UKHSA")
LITERATURE = ("PubMed", "Preprint")
DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def _country_docs(sources, event_type=None, since=None) -> pd.DataFrame:
    q = f"""SELECT DISTINCT ent.value AS country, d.id AS did, {DATE_EXPR} AS day,
                   d.source AS source, d.title AS title, d.url AS url
            FROM documents d
            JOIN extractions e ON e.document_id=d.id AND e.is_active=1
            JOIN entities ent ON ent.document_id=d.id AND ent.entity_type='country'
            WHERE d.source IN ({','.join('?'*len(sources))})"""
    params = list(sources)
    if event_type:
        q += " AND e.event_type=?"; params.append(event_type)
    if since:
        q += f" AND {DATE_EXPR} >= ?"; params.append(since)
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["country"] = df["country"].map(canonical_country)
    return df


def active_outbreaks(recent_days: int = 45, limit: int = 80) -> list[dict]:
    since = (date.today() - timedelta(days=recent_days)).isoformat()
    df = _country_docs(OFFICIAL, event_type="Outbreak", since=since)
    if df.empty:
        return []
    df = df.sort_values("day", ascending=False)
    return df.head(limit).to_dict("records")


def country_outbreak_labels(recent_days: int = 45) -> set[str]:
    since = (date.today() - timedelta(days=recent_days)).isoformat()
    df = _country_docs(OFFICIAL, event_type="Outbreak", since=since)
    return set(df["country"]) if not df.empty else set()


def literature_signal(feature_days: int = 90) -> pd.Series:
    since = (date.today() - timedelta(days=feature_days)).isoformat()
    df = _country_docs(LITERATURE, since=since)
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("country")["did"].nunique()


def _rank_auc(pos: list[float], neg: list[float]) -> float | None:
    """AUC = P(signal_pos > signal_neg) via the rank-sum identity."""
    n_pos, n_neg = len(pos), len(neg)
    if n_pos == 0 or n_neg == 0:
        return None
    allv = [(v, 1) for v in pos] + [(v, 0) for v in neg]
    allv.sort(key=lambda t: t[0])
    # average ranks (handle ties)
    ranks, i = {}, 0
    vals = [v for v, _ in allv]
    import statistics  # noqa
    rank_list = [0.0] * len(allv)
    j = 0
    while j < len(allv):
        k = j
        while k + 1 < len(allv) and allv[k + 1][0] == allv[j][0]:
            k += 1
        avg = (j + k) / 2 + 1  # 1-based average rank
        for m in range(j, k + 1):
            rank_list[m] = avg
        j = k + 1
    rank_pos = sum(r for r, (_, lab) in zip(rank_list, allv) if lab == 1)
    auc = (rank_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return round(auc, 3)


def association(recent_days: int = 45, feature_days: int = 90) -> dict:
    labels = country_outbreak_labels(recent_days)
    sig = literature_signal(feature_days)
    countries = set(sig.index) | labels
    if len(countries) < 6 or not labels:
        return {"ok": False, "reason": "not enough countries / outbreaks yet",
                "n_countries": len(countries), "n_outbreak": len(labels)}
    rows = [{"country": c, "lit_signal": int(sig.get(c, 0)),
             "official_outbreak": 1 if c in labels else 0} for c in countries]
    df = pd.DataFrame(rows)
    pos = df[df["official_outbreak"] == 1]["lit_signal"].tolist()
    neg = df[df["official_outbreak"] == 0]["lit_signal"].tolist()
    return {
        "ok": True,
        "n_countries": len(df), "n_outbreak": int(df["official_outbreak"].sum()),
        "mean_signal_outbreak": round(sum(pos) / len(pos), 2) if pos else 0,
        "mean_signal_no_outbreak": round(sum(neg) / len(neg), 2) if neg else 0,
        "rank_auc": _rank_auc(pos, neg),
        "table": df.sort_values(["official_outbreak", "lit_signal"], ascending=False),
    }


if __name__ == "__main__":
    print("active outbreaks:", len(active_outbreaks()))
    a = association()
    print({k: v for k, v in a.items() if k != "table"})
