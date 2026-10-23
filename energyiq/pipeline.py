"""End-to-end analysis: data -> baseline -> anomalies -> peaks/drivers -> recommendations."""
from __future__ import annotations

import pandas as pd

from .analytics import change_point_model, drift, load_shape, peak_analysis
from .anomaly import detect
from .baseline import fit_baseline
from .ingest import EnergyData
from .recommend import recommend


def analyze_meter(y: pd.Series, weather: pd.DataFrame, temp_col: str | None,
                  z_thr: float = 3.5, meter: str = "") -> dict:
    y = y.dropna()
    fit = fit_baseline(y, weather)
    det = detect(y, fit["expected"], weather, z_thr=z_thr, meter=meter)
    return {
        "y": y, "expected": fit["expected"], "importance": fit["importance"], "metrics": fit["metrics"],
        "z": det["z"], "sign": det["sign"], "events": det["events"],
        "shape": load_shape(y),
        "cp": change_point_model(y, weather[temp_col]) if temp_col else None,
        "drift": drift(y, fit["expected"]),
    }


def analyze(data: EnergyData, z_thr: float = 3.5, tariff: float = 8.0, co2: float = 0.71,
            demand_charge: float = 400.0) -> dict:
    res = {"meters": {}}
    for m in data.meters.columns:
        res["meters"][m] = analyze_meter(data.meters[m], data.weather, data.temp_col, z_thr, m)
    res["peaks"] = peak_analysis(data.meters)
    evs = [r["events"] for r in res["meters"].values() if len(r["events"])]
    res["events"] = pd.concat(evs, ignore_index=True) if evs else pd.DataFrame()
    res["recs"] = recommend(res, tariff, co2, demand_charge)
    return res
