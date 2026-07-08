"""
Risk scoring framework (Phase 4) — transparent and validation-first.

Rather than invent an arbitrary 0-100 index, this module:

  1. builds interpretable per-country AMR signal features from the platform
     (recent AMR document volume + velocity), reporting-bias aware;
  2. produces a composite RISK signal (percentile-ranked, clearly labelled as a
     signal index, NOT a validated probability);
  3. CHECKS that signal against ground truth via construct validity — the
     Spearman correlation between the platform signal and WHO GHO / GLASS
     measured resistance (%). If that correlation is weak, the page says so.
  4. reports predictive skill for the self-contained surge task via backtest.

Honest status: on a young corpus the per-country signal is sparse and its
correlation with measured resistance is expected to be weak; this is itself a
finding (reporting bias) and strengthens as data accumulates. The AMR-escalation
*predictive* task activates once the platform has multi-year history overlapping
new GLASS releases.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import db
from extract.dictionaries import COUNTRY_ISO3, canonical_country

# pathogens/labels that mark a document as AMR-relevant
AMR_PATHOGENS = {"MRSA", "VRE", "VRSA", "CRE", "CRKP", "CRAB", "CRPA", "ESBL",
                 "Candida auris"}
DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def _country_features(recent_days: int = 60) -> pd.DataFrame:
    """Per-country: total docs, AMR docs (recent & previous), velocity, share."""
    today = date.today()
    recent_cut = (today - timedelta(days=recent_days)).isoformat()
    prev_cut = (today - timedelta(days=2 * recent_days)).isoformat()

    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT c.value AS country, d.id AS did, {DATE_EXPR} AS day,
                       EXISTS(SELECT 1 FROM entities g WHERE g.document_id=d.id
                              AND (g.entity_type='resistance_gene'
                                   OR (g.entity_type='pathogen' AND g.value IN
                                       ({','.join('?'*len(AMR_PATHOGENS))})))) AS is_amr
                FROM documents d
                JOIN entities c ON c.document_id=d.id AND c.entity_type='country'
            """, tuple(AMR_PATHOGENS)).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df["country"] = df["country"].map(canonical_country)
    df["is_amr"] = df["is_amr"].astype(int)
    df["period"] = df["day"].apply(
        lambda d: "recent" if d >= recent_cut else ("prev" if d >= prev_cut else "old"))

    grp = df.groupby("country")
    out = pd.DataFrame({
        "total_docs": grp["did"].nunique(),
        "amr_docs": grp.apply(lambda g: g[g["is_amr"] == 1]["did"].nunique(), include_groups=False),
        "recent_amr": grp.apply(
            lambda g: g[(g["is_amr"] == 1) & (g["period"] == "recent")]["did"].nunique(),
            include_groups=False),
        "prev_amr": grp.apply(
            lambda g: g[(g["is_amr"] == 1) & (g["period"] == "prev")]["did"].nunique(),
            include_groups=False),
    })
    out["velocity"] = out["recent_amr"] - out["prev_amr"]
    out["amr_share"] = (out["amr_docs"] / out["total_docs"]).round(3)
    out["iso3"] = out.index.map(COUNTRY_ISO3.get)
    return out.reset_index()


def country_risk(recent_days: int = 60, min_docs: int = 1) -> pd.DataFrame:
    """Composite (percentile-ranked) risk signal per country. Signal, not proof."""
    feat = _country_features(recent_days)
    if feat.empty:
        return feat
    f = feat[feat["total_docs"] >= min_docs].copy()
    if f.empty:
        return f
    # percentile ranks of volume and velocity (transparent, equal weight)
    f["vol_rank"] = f["recent_amr"].rank(pct=True)
    f["vel_rank"] = f["velocity"].rank(pct=True)
    f["risk_signal"] = ((0.5 * f["vol_rank"] + 0.5 * f["vel_rank"]) * 100).round(0)
    return f.sort_values("risk_signal", ascending=False).reset_index(drop=True)


def latest_reference(indicator: str = "AMR_INFECT_MRSA") -> pd.DataFrame:
    """Most recent WHO GHO resistance value per country."""
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT country_iso3, country, year, value FROM amr_reference r
               WHERE indicator=? AND year=(
                   SELECT MAX(year) FROM amr_reference r2
                   WHERE r2.country_iso3=r.country_iso3 AND r2.indicator=?)""",
            (indicator, indicator)).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def construct_validity(indicator: str = "AMR_INFECT_MRSA",
                       recent_days: int = 90) -> dict:
    """
    Spearman correlation between the platform's per-country AMR signal and WHO
    GHO measured resistance (%). Returns the coefficient, N, and paired data.
    """
    feat = _country_features(recent_days)
    ref = latest_reference(indicator)
    if feat.empty or ref.empty:
        return {"ok": False, "reason": "insufficient data"}
    merged = feat.merge(ref, left_on="iso3", right_on="country_iso3",
                        suffixes=("", "_ref"))
    merged = merged[(merged["amr_docs"] > 0) & merged["value"].notna()]
    if len(merged) < 5:
        return {"ok": False, "reason": f"only {len(merged)} countries overlap — "
                "need more accumulated data", "n": len(merged)}
    # Spearman rho = Pearson correlation of the ranks. Computing it via ranks
    # keeps us on pandas alone (pandas' method="spearman" pulls in scipy, which
    # isn't installed on Streamlit Cloud).
    rho = merged["amr_docs"].rank().corr(merged["value"].rank())
    rho_share = merged["amr_share"].rank().corr(merged["value"].rank())
    return {
        "ok": True, "indicator": indicator, "n": len(merged),
        "spearman_volume": round(float(rho), 3),
        "spearman_share": round(float(rho_share), 3),
        "pairs": merged[["country", "amr_docs", "amr_share", "value"]]
                 .rename(columns={"value": "gho_resistance_%"})
                 .sort_values("gho_resistance_%", ascending=False),
    }


def surge_skill(top_n: int = 6) -> dict:
    """Aggregate backtest skill for the surge task vs naive baseline."""
    from analysis import forecast
    from analysis.trends import top_entities
    pathogens = [r["value"] for r in top_entities("pathogen", 3650, top_n).to_dict("records")]
    lin, naive, k = 0.0, 0.0, 0
    for p in pathogens:
        r = forecast.forecast("pathogen", p, horizon=4)
        ev = r.get("evaluation") or {}
        if ev.get("linear_mae") is not None:
            lin += ev["linear_mae"]; naive += ev["naive_mae"]; k += 1
    if not k:
        return {"ok": False}
    return {"ok": True, "n_pathogens": k,
            "mean_linear_mae": round(lin / k, 2),
            "mean_naive_mae": round(naive / k, 2),
            "beats_naive": lin <= naive}


if __name__ == "__main__":
    print(country_risk().head(10).to_string(index=False))
    print("\nConstruct validity:", {k: v for k, v in construct_validity().items() if k != "pairs"})
    print("Surge skill:", surge_skill())
