"""Reproducible external validation for VIGIL's text-derived AMR signals.

This module deliberately does *not* claim prediction.  It audits the dated
corpus, constructs country-year signals only from documents available in that
year, and evaluates their concurrent association with independently reported
WHO GHO/GLASS resistance indicators.  It refuses to report a result when the
time overlap is too sparse.

The output is intended to be the auditable foundation for the no-human-label
methodology paper: "Open-source AMR intelligence is biased: externally
validating and calibrating text-derived surveillance signals".
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

import config
import db
from extract.dictionaries import COUNTRY_ISO3, canonical_country

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"
AMR_PATHOGENS = ("MRSA", "VRE", "VRSA", "CRE", "CRKP", "CRAB", "CRPA", "ESBL", "Candida auris")
DEFAULT_INDICATORS = ("AMR_INFECT_MRSA", "AMR_INFECT_ECOLI")


def _rank_corr(left: pd.Series, right: pd.Series) -> float | None:
    if len(left) < 5 or left.nunique() < 2 or right.nunique() < 2:
        return None
    value = left.rank(method="average").corr(right.rank(method="average"))
    return round(float(value), 3) if pd.notna(value) else None


def corpus_audit(as_of: date | None = None) -> dict:
    """Return date integrity and reference-overlap diagnostics.

    Dates after ``as_of`` are excluded from all analyses.  A date gap is a
    warning rather than an error: the manuscript must describe it and avoid
    calling a sparse period a longitudinal evaluation.
    """
    as_of = as_of or date.today()
    with db.get_conn() as conn:
        docs = pd.DataFrame([dict(r) for r in conn.execute(
            f"SELECT d.id, d.source, {DATE_EXPR} AS day FROM documents d"
        ).fetchall()])
        refs = pd.DataFrame([dict(r) for r in conn.execute(
            "SELECT indicator, year, country_iso3, value FROM amr_reference"
        ).fetchall()])
    if docs.empty:
        return {"ok": False, "reason": "No documents in corpus."}
    docs["day"] = pd.to_datetime(docs["day"], errors="coerce", utc=True)
    cutoff = pd.Timestamp(as_of, tz="UTC") + pd.Timedelta(days=1)
    future = docs[docs["day"] >= cutoff]
    valid = docs[docs["day"].notna() & (docs["day"] < cutoff)].copy()
    valid["year"] = valid["day"].dt.year.astype(int)
    yearly = valid.groupby("year")["id"].nunique().to_dict()
    min_year, max_year = int(valid["year"].min()), int(valid["year"].max())
    missing_years = [y for y in range(min_year, max_year + 1) if yearly.get(y, 0) == 0]
    sparse_years = {str(y): int(n) for y, n in yearly.items() if n < 30}
    ref_years = sorted(int(y) for y in refs["year"].dropna().unique()) if not refs.empty else []
    overlap = sorted(set(yearly) & set(ref_years))
    return {
        "ok": True,
        "as_of": as_of.isoformat(),
        "n_documents_total": int(len(docs)),
        "n_documents_usable": int(len(valid)),
        "n_future_dated_documents_excluded": int(len(future)),
        "n_invalid_or_missing_dates_excluded": int(docs["day"].isna().sum()),
        "document_year_counts": {str(int(k)): int(v) for k, v in yearly.items()},
        "missing_document_years": missing_years,
        "sparse_document_years_lt30": sparse_years,
        "reference_years": ref_years,
        "document_reference_overlap_years": overlap,
        "ready_for_longitudinal_prediction": len(overlap) >= 4 and not missing_years,
    }


def country_year_features(as_of: date | None = None) -> pd.DataFrame:
    """Build dated, country-level text signals without using WHO outcomes.

    ``amr_docs`` uses the frozen entity pipeline: a resistance-mechanism entity
    or one of the predefined AMR phenotype/pathogen labels.  ``amr_share``
    divides by all country-tagged documents in that country-year, reducing the
    influence of country research volume.
    """
    as_of = as_of or date.today()
    placeholders = ",".join("?" * len(AMR_PATHOGENS))
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT DISTINCT d.id AS document_id, c.value AS country,
                       {DATE_EXPR} AS day,
                       EXISTS(
                           SELECT 1 FROM entities a
                           WHERE a.document_id=d.id AND (
                               a.entity_type='resistance_gene' OR
                               (a.entity_type='pathogen' AND a.value IN ({placeholders}))
                           )
                       ) AS is_amr
                FROM documents d
                JOIN entities c ON c.document_id=d.id AND c.entity_type='country'""",
            AMR_PATHOGENS,
        ).fetchall()
    frame = pd.DataFrame([dict(r) for r in rows])
    if frame.empty:
        return frame
    frame["day"] = pd.to_datetime(frame["day"], errors="coerce", utc=True)
    cutoff = pd.Timestamp(as_of, tz="UTC") + pd.Timedelta(days=1)
    frame = frame[frame["day"].notna() & (frame["day"] < cutoff)].copy()
    frame["country"] = frame["country"].map(canonical_country)
    frame["iso3"] = frame["country"].map(COUNTRY_ISO3.get)
    frame = frame[frame["iso3"].notna()].copy()
    frame["year"] = frame["day"].dt.year.astype(int)
    grouped = frame.groupby(["year", "country", "iso3"], as_index=False).agg(
        total_docs=("document_id", "nunique"),
        amr_docs=("is_amr", "sum"),
    )
    grouped["amr_share"] = grouped["amr_docs"] / grouped["total_docs"]
    return grouped.sort_values(["year", "country"]).reset_index(drop=True)


def annual_external_validity(indicator: str, min_docs: int = 1,
                             as_of: date | None = None) -> dict:
    """Evaluate same-year signal association with an independent WHO indicator.

    This is a construct-validity analysis, *not* a forecast.  It returns
    ``ok=False`` for sparse overlap, rather than silently reporting unstable
    correlations.
    """
    features = country_year_features(as_of)
    with db.get_conn() as conn:
        refs = pd.DataFrame([dict(r) for r in conn.execute(
            """SELECT country_iso3 AS iso3, country AS reference_country,
                      year, value
               FROM amr_reference WHERE indicator=?""", (indicator,)
        ).fetchall()])
    if features.empty or refs.empty:
        return {"ok": False, "reason": "No usable feature or reference data."}
    merged = features.merge(refs, on=["iso3", "year"], how="inner")
    merged = merged[(merged["total_docs"] >= min_docs) & merged["value"].notna()].copy()
    yearly_rows = []
    for year, subset in merged.groupby("year"):
        yearly_rows.append({
            "year": int(year), "n_country_years": int(len(subset)),
            "spearman_amr_docs": _rank_corr(subset["amr_docs"], subset["value"]),
            "spearman_amr_share": _rank_corr(subset["amr_share"], subset["value"]),
        })
    pooled_docs = _rank_corr(merged["amr_docs"], merged["value"])
    pooled_share = _rank_corr(merged["amr_share"], merged["value"])
    enough = len(merged) >= 30 and len(yearly_rows) >= 3
    return {
        "ok": enough,
        "analysis": "same-year external construct validity; not a forecast",
        "indicator": indicator,
        "n_country_years": int(len(merged)),
        "n_years": int(len(yearly_rows)),
        "pooled_spearman_amr_docs": pooled_docs,
        "pooled_spearman_amr_share": pooled_share,
        "yearly": yearly_rows,
        "reason": None if enough else (
            "Insufficient dated country-year overlap for a reliable longitudinal claim. "
            "Expand the historical corpus before fitting predictive models."
        ),
        "pairs": merged.sort_values(["year", "country"]),
    }


def write_research_bundle(output_dir: Path | None = None,
                          as_of: date | None = None) -> Path:
    """Write an auditable, dated paper-readiness bundle under ``reports/``."""
    as_of = as_of or date.today()
    output_dir = output_dir or (config.REPORTS_DIR / f"paper2_validation_{as_of.isoformat()}")
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = corpus_audit(as_of)
    (output_dir / "corpus_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    features = country_year_features(as_of)
    features.to_csv(output_dir / "country_year_features.csv", index=False)
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "audit": audit, "indicators": {}}
    for indicator in DEFAULT_INDICATORS:
        result = annual_external_validity(indicator, as_of=as_of)
        pairs = result.pop("pairs", pd.DataFrame())
        pairs.to_csv(output_dir / f"{indicator}_pairs.csv", index=False)
        summary["indicators"][indicator] = result
    (output_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# VIGIL external-validation research audit", "",
        f"Generated: {summary['generated_at_utc']}", "",
        "## Data integrity", "",
        f"- Usable documents: {audit.get('n_documents_usable', 0)}",
        f"- Future-dated documents excluded: {audit.get('n_future_dated_documents_excluded', 0)}",
        f"- Document/reference overlap years: {audit.get('document_reference_overlap_years', [])}",
        f"- Longitudinal prediction ready: {audit.get('ready_for_longitudinal_prediction', False)}", "",
        "## External validity", "",
    ]
    for indicator, result in summary["indicators"].items():
        lines.extend([
            f"### {indicator}", "",
            f"- Country-years: {result.get('n_country_years', 0)}",
            f"- Pooled Spearman, raw AMR-document count: {result.get('pooled_spearman_amr_docs')}",
            f"- Pooled Spearman, AMR-document share: {result.get('pooled_spearman_amr_share')}",
            f"- Status: {'ready for descriptive construct-validity reporting' if result.get('ok') else result.get('reason')}", "",
        ])
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


if __name__ == "__main__":
    print(write_research_bundle())
