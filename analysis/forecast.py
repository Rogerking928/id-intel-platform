"""
Minimal forecasting prototype (Paper 2 direction).

Goal: given a pathogen (or any tracked entity), forecast its weekly "discussion
volume" (number of documents mentioning it) for the next few weeks.

This is deliberately a TRANSPARENT BASELINE, not a black box:
  * model     = ordinary least-squares linear trend on weekly counts
  * baselines = naive last-value, and 4-week moving average
  * evaluation = rolling backtest MAE, reported next to the baselines so a
    reader can see whether the model actually beats "just guess the last value"
  * uncertainty = ±1.96 * residual std, clipped at 0 (counts can't be negative)

It runs today on a small dataset and becomes more reliable as the platform
accumulates weeks of data. Roadmap: swap the linear model for ARIMA / Prophet /
a Poisson GLM once there is >= ~1 year of history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import db

DATE_EXPR = "COALESCE(NULLIF(d.published_date,''), substr(d.fetched_at,1,10))"


def weekly_series(entity_type: str, value: str, weeks: int = 26) -> pd.Series:
    """Continuous weekly document counts for one entity (missing weeks = 0)."""
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT {DATE_EXPR} AS day, d.id AS did
                FROM entities e JOIN documents d ON d.id = e.document_id
                WHERE e.entity_type = ? AND e.value = ?""",
            (entity_type, value),
        ).fetchall()
    if not rows:
        return pd.Series(dtype="float64")
    df = pd.DataFrame([dict(r) for r in rows])
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df = df.dropna(subset=["day"])
    if df.empty:
        return pd.Series(dtype="float64")
    counts = df.groupby(pd.Grouper(key="day", freq="W-MON"))["did"].nunique()
    # restrict to the most recent `weeks`, on a gap-free weekly index
    end = counts.index.max()
    start = end - pd.Timedelta(weeks=weeks - 1)
    idx = pd.date_range(start=start, end=end, freq="W-MON")
    return counts.reindex(idx, fill_value=0).astype(float)


def _mae(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred))) if len(actual) else float("nan")


def _linear_fit(y: np.ndarray):
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return slope, intercept


def _backtest(y: np.ndarray, horizon: int) -> dict:
    """Hold out the last `horizon` weeks; compare linear vs naive baselines."""
    if len(y) < horizon + 3:
        return {}
    train, test = y[:-horizon], y[-horizon:]
    slope, intercept = _linear_fit(train)
    fx = np.arange(len(train), len(train) + horizon)
    lin_pred = np.clip(slope * fx + intercept, 0, None)
    naive_pred = np.full(horizon, train[-1])                 # last value
    ma_pred = np.full(horizon, train[-min(4, len(train)):].mean())  # 4-wk mean
    return {
        "linear_mae": round(_mae(test, lin_pred), 2),
        "naive_mae": round(_mae(test, naive_pred), 2),
        "movavg_mae": round(_mae(test, ma_pred), 2),
    }


def forecast(entity_type: str, value: str, horizon: int = 4, weeks: int = 26) -> dict:
    """Return history + forecast + evaluation for one entity."""
    s = weekly_series(entity_type, value, weeks=weeks)
    if s.empty or len(s) < 4 or s.sum() < 3:
        return {"ok": False,
                "reason": "Not enough history yet — needs a few weeks of data. "
                          "This fills in as the platform runs daily.",
                "entity_type": entity_type, "value": value}

    y = s.values.astype(float)
    slope, intercept = _linear_fit(y)
    x_future = np.arange(len(y), len(y) + horizon)
    mean = np.clip(slope * x_future + intercept, 0, None)

    fitted = slope * np.arange(len(y)) + intercept
    resid_std = float(np.std(y - fitted, ddof=1)) if len(y) > 2 else 0.0
    lo = np.clip(mean - 1.96 * resid_std, 0, None)
    hi = mean + 1.96 * resid_std

    last_week = s.index.max()
    future_weeks = pd.date_range(last_week + pd.Timedelta(weeks=1),
                                 periods=horizon, freq="W-MON")

    metrics = _backtest(y, horizon)
    direction = ("rising" if slope > 0.15 else
                 "declining" if slope < -0.15 else "flat")

    return {
        "ok": True,
        "entity_type": entity_type, "value": value, "horizon": horizon,
        "slope_per_week": round(float(slope), 3),
        "direction": direction,
        "history": {"weeks": [d.date().isoformat() for d in s.index],
                    "counts": [int(v) for v in y]},
        "forecast": {"weeks": [d.date().isoformat() for d in future_weeks],
                     "mean": [round(float(v), 2) for v in mean],
                     "lo": [round(float(v), 2) for v in lo],
                     "hi": [round(float(v), 2) for v in hi]},
        "evaluation": metrics,   # backtest MAE: linear vs naive vs moving-avg
        "model": "OLS linear trend on weekly counts (baseline)",
    }


def forecast_frame(result: dict) -> pd.DataFrame:
    """Flatten a forecast() result into a plottable long DataFrame."""
    if not result.get("ok"):
        return pd.DataFrame()
    h = result["history"]; f = result["forecast"]
    hist = pd.DataFrame({"week": h["weeks"], "value": h["counts"],
                         "kind": "actual", "lo": h["counts"], "hi": h["counts"]})
    fc = pd.DataFrame({"week": f["weeks"], "value": f["mean"],
                       "kind": "forecast", "lo": f["lo"], "hi": f["hi"]})
    out = pd.concat([hist, fc], ignore_index=True)
    out["week"] = pd.to_datetime(out["week"])
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(forecast("pathogen", "CRE", horizon=4), indent=2))
