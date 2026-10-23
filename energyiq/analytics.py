"""Peak-load analysis and consumption drivers."""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------- peaks ----------

def peak_analysis(meters: pd.DataFrame, q: float = 0.95) -> dict:
    total = meters.sum(axis=1, min_count=1).dropna()
    thr = float(total.quantile(q))
    is_peak = total >= thr
    heat = total.groupby([total.index.dayofweek, total.index.hour]).mean().unstack()
    heat.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][: len(heat)]
    peak_idx = total.idxmax()
    share = (meters.loc[peak_idx] / meters.loc[peak_idx].sum() * 100).sort_values(ascending=False)
    peak_hours = total[is_peak]
    hour_hist = peak_hours.groupby(peak_hours.index.hour).size().reindex(range(24), fill_value=0)
    daily_peak = total.resample("D").max()
    return {
        "total": total, "threshold": thr, "is_peak": is_peak, "heatmap": heat,
        "ldc": np.sort(total.values)[::-1],
        "peak_kw": float(total.max()), "peak_time": peak_idx,
        "avg_kw": float(total.mean()),
        "load_factor": float(total.mean() / total.max()),
        "par": float(total.max() / total.mean()),
        "peak_share": share, "peak_hour_hist": hour_hist,
        "top_peaks": total.nlargest(10),
        "daily_peak": daily_peak,
        "peak_energy_share": float(total[is_peak].sum() / total.sum() * 100),
        "hours_above_thr": int(is_peak.sum()),
    }


# ---------- drivers ----------

def change_point_model(y: pd.Series, temp: pd.Series) -> dict | None:
    """Daily energy vs daily mean temp; 3-parameter cooling + heating change-point fit."""
    d = pd.DataFrame({"e": y.resample("D").sum(min_count=20), "t": temp.resample("D").mean()}).dropna()
    if len(d) < 30:
        return None
    best = None
    for tb in np.arange(np.percentile(d.t, 10), np.percentile(d.t, 90), 0.25):
        X = np.c_[np.ones(len(d)), np.maximum(d.t - tb, 0), np.maximum(tb - d.t, 0)]
        coef, *_ = np.linalg.lstsq(X, d.e.values, rcond=None)
        sse = ((X @ coef - d.e.values) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, tb, coef)
    sse, tb, coef = best
    r2 = 1 - sse / ((d.e - d.e.mean()) ** 2).sum()
    cool_slope, heat_slope = float(max(coef[1], 0)), float(max(coef[2], 0))
    weather_kwh = cool_slope * np.maximum(d.t - tb, 0) + heat_slope * np.maximum(tb - d.t, 0)
    return {
        "balance_c": float(tb), "base_kwh_day": float(coef[0]),
        "cool_kwh_per_c_day": cool_slope, "heat_kwh_per_c_day": heat_slope,
        "r2": float(r2), "weather_share": float(weather_kwh.sum() / d.e.sum() * 100),
        "cooling_days": int((d.t > tb).sum()), "daily": d, "n_days": len(d),
        "cooling_degree_days": float(np.maximum(d.t - tb, 0).sum()),
    }


def load_shape(y: pd.Series) -> dict:
    h = y.index.hour
    wk = y.index.dayofweek >= 5
    night = y[(h >= 1) & (h <= 4)].mean()
    day = y[(h >= 9) & (h <= 17) & ~wk].mean()
    weekday_daily = y[~wk].resample("D").sum(min_count=20).dropna()
    weekend_daily = y[wk].resample("D").sum(min_count=20).dropna()
    return {
        "baseload": float(y.quantile(0.05)),
        "baseload_share": float(y.quantile(0.05) / y.mean() * 100),
        "night_kw": float(night), "day_kw": float(day),
        "night_day_ratio": float(night / day) if day else np.nan,
        "weekend_weekday_ratio": float(weekend_daily.mean() / weekday_daily.mean())
        if len(weekend_daily) and len(weekday_daily) else np.nan,
        "profile_weekday": y[~wk].groupby(y[~wk].index.hour).mean(),
        "profile_weekend": y[wk].groupby(y[wk].index.hour).mean(),
    }


def drift(y: pd.Series, expected: pd.Series) -> pd.Series:
    """Monthly weather-normalised performance: % above/below the model's expectation."""
    r = pd.DataFrame({"y": y, "e": expected}).dropna().resample("MS").sum()
    return (r.y / r.e - 1) * 100
