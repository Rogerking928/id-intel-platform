"""
WHO Global Health Observatory (GHO) AMR reference collector.

Fetches GLASS-derived antimicrobial-resistance indicators (free OData API, no
key) — the country-year resistance percentages we use as GROUND TRUTH when
validating the platform's risk score. No manual download needed.

Indicators:
  AMR_INFECT_MRSA  — % of bloodstream infections due to MRSA
  AMR_INFECT_ECOLI — % of BSI due to E. coli resistant to 3rd-gen cephalosporins
"""
import config
import db
from collectors.base import get
from extract.dictionaries import ISO3_TO_COUNTRY

GHO_API = "https://ghoapi.azureedge.net/api/"
INDICATORS = ["AMR_INFECT_MRSA", "AMR_INFECT_ECOLI"]


def collect() -> int:
    """Fetch indicators and upsert into amr_reference. Returns rows stored."""
    db.init_db()
    stored = 0
    for ind in INDICATORS:
        try:
            rows = get(GHO_API + ind).json().get("value", [])
        except Exception as exc:  # noqa: BLE001
            print(f"  [GHO] {ind} failed: {exc}")
            continue
        with db.get_conn() as conn:
            for r in rows:
                iso3 = r.get("SpatialDim")
                year = r.get("TimeDim")
                val = r.get("NumericValue")
                if not iso3 or val is None or r.get("SpatialDimType") != "COUNTRY":
                    continue
                conn.execute(
                    """INSERT OR REPLACE INTO amr_reference
                       (country_iso3, country, indicator, year, value, source)
                       VALUES (?,?,?,?,?, 'WHO GHO')""",
                    (iso3, ISO3_TO_COUNTRY.get(iso3), ind, year, float(val)),
                )
                stored += 1
    return stored


if __name__ == "__main__":
    n = collect()
    print(f"Stored {n} AMR reference data points.")
