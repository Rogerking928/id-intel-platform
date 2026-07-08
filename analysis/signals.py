"""
Signal detection (Phase 2: real trend intelligence, not just counts).

Two capabilities:

  1. growth_rate()  — period-over-period % change, so you rank by how FAST
     something is rising, not just how many documents mention it.
        e.g. CRKP  prev=80  recent=200  ->  +150%

  2. emerging_signals() — flags entities that were near-absent in the baseline
     window and then spiked recently. This is the "used to be quiet, suddenly
     loud" detector, the first step toward a novelty / early-warning system.

Both work on the existing entities table and get stronger as the platform
accumulates history. Honest note: on a young dataset counts are small, so read
these as directional, not definitive.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

import db

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def _entity_days(entity_type: str) -> pd.DataFrame:
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT e.value AS value, {DATE_EXPR} AS day, d.id AS did
                FROM entities e JOIN documents d ON d.id = e.document_id
                WHERE e.entity_type = ?""",
            (entity_type,),
        ).fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
        df = df.dropna(subset=["day"])
    return df


def growth_rate(entity_type: str, period_days: int = 30, top: int = 15,
                min_recent: int = 2) -> pd.DataFrame:
    """Rank entities by % growth: recent period vs the preceding period."""
    df = _entity_days(entity_type)
    if df.empty:
        return pd.DataFrame(columns=["value", "previous", "recent", "growth_%", "flag"])
    today = pd.Timestamp(date.today())
    recent_start = today - pd.Timedelta(days=period_days)
    prev_start = today - pd.Timedelta(days=2 * period_days)

    recent = (df[df["day"] >= recent_start].groupby("value")["did"].nunique())
    prev = (df[(df["day"] >= prev_start) & (df["day"] < recent_start)]
            .groupby("value")["did"].nunique())
    out = pd.DataFrame({"previous": prev, "recent": recent}).fillna(0).astype(int)
    out = out[out["recent"] >= min_recent]
    if out.empty:
        return pd.DataFrame(columns=["value", "previous", "recent", "growth_%", "flag"])

    def pct(row):
        if row["previous"] == 0:
            return np.nan  # brand new -> no finite %
        return round((row["recent"] - row["previous"]) / row["previous"] * 100, 0)

    out["growth_%"] = out.apply(pct, axis=1)
    out["flag"] = np.where(out["previous"] == 0, "NEW",
                           np.where(out["growth_%"] >= 50, "▲ rising", ""))
    # sort: NEW first (by recent volume), then by growth %
    out = out.reset_index().rename(columns={"index": "value"})
    out["_sortkey"] = out["growth_%"].fillna(10_000 + out["recent"])
    out = out.sort_values("_sortkey", ascending=False).drop(columns="_sortkey")
    return out.head(top).reset_index(drop=True)


def emerging_signals(entity_types=("pathogen", "resistance_gene", "antibiotic"),
                     baseline_weeks: int = 20, recent_weeks: int = 4,
                     min_recent: int = 2, ratio: float = 3.0) -> pd.DataFrame:
    """
    Flag entities quiet in the baseline window but spiking in the recent window.

    A signal fires when recent activity >= `min_recent` AND either there was no
    baseline activity at all, or recent-per-week is >= `ratio`x the baseline
    per-week rate.
    """
    results = []
    today = pd.Timestamp(date.today())
    recent_start = today - pd.Timedelta(weeks=recent_weeks)
    base_start = today - pd.Timedelta(weeks=baseline_weeks + recent_weeks)

    for etype in entity_types:
        df = _entity_days(etype)
        if df.empty:
            continue
        base = df[(df["day"] >= base_start) & (df["day"] < recent_start)]
        rec = df[df["day"] >= recent_start]
        base_rate = base.groupby("value")["did"].nunique() / max(baseline_weeks, 1)
        rec_ct = rec.groupby("value")["did"].nunique()
        for value, recent in rec_ct.items():
            if recent < min_recent:
                continue
            b_rate = float(base_rate.get(value, 0.0))
            rec_rate = recent / max(recent_weeks, 1)
            if b_rate == 0 or rec_rate >= ratio * b_rate:
                score = round(rec_rate / (b_rate + 0.25), 1)  # +0.25 smooths /0
                results.append({
                    "type": etype, "value": value,
                    "baseline_/wk": round(b_rate, 2),
                    "recent_total": int(recent),
                    "surge_score": score,
                    "signal": "🚨 EMERGING" if b_rate == 0 else "▲ surge",
                })
    out = pd.DataFrame(results)
    if out.empty:
        return pd.DataFrame(columns=["type", "value", "baseline_/wk",
                                     "recent_total", "surge_score", "signal"])
    return out.sort_values(["surge_score", "recent_total"], ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    print("=== Growth rate (pathogens, 30d vs prev 30d) ===")
    print(growth_rate("pathogen").to_string(index=False))
    print("\n=== Emerging signals ===")
    print(emerging_signals().to_string(index=False))
