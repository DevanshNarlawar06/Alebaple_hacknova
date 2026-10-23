"""Context-aware anomaly detection on residuals (actual - expected).

A residual is judged against the *normal* residual spread for that hour of day (robust MAD),
so a busy afternoon is not an anomaly but an unusual 3 a.m. load is.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

AFTER_HOURS = set(range(0, 6)) | {22, 23}


def robust_z(resid: pd.Series, y: pd.Series) -> pd.Series:
    hours = resid.index.hour
    med = resid.groupby(hours).transform("median")
    mad = (resid - med).abs().groupby(hours).transform("median") * 1.4826
    floor = 0.02 * y.abs().median()  # avoid dividing by ~0 on very flat meters
    return (resid - med) / np.maximum(mad, floor)


def detect(y: pd.Series, expected: pd.Series, weather: pd.DataFrame | None = None,
           z_thr: float = 3.5, sustained_thr: float = 2.0, window: int = 6,
           meter: str = "") -> dict:
    y, expected = y.align(expected, join="inner")
    resid = y - expected
    z = robust_z(resid, y)
    roll = z.rolling(window, center=True, min_periods=window // 2).mean()
    flag_pos = (z > z_thr) | (roll > sustained_thr)
    flag_neg = (z < -z_thr) | (roll < -sustained_thr)
    sign = pd.Series(0, index=y.index)
    sign[flag_pos] = 1
    sign[flag_neg & ~flag_pos] = -1

    events = []
    tcol = None
    if weather is not None:
        tcol = next((c for c in weather.columns if "temp" in c.lower()), None)
    idx = y.index
    s = sign.values
    i = 0
    while i < len(s):
        if s[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < len(s) and (s[j + 1] == s[i] or (j + 2 < len(s) and s[j + 2] == s[i] and s[j + 1] == 0)):
            j += 1
        sl = slice(i, j + 1)
        hrs = idx[sl]
        exc = float(resid.iloc[sl].sum())
        exp_sum = float(expected.iloc[sl].sum())
        dur = len(hrs)
        if s[i] < 0:
            etype = "Drop / outage" if exc < -0.5 * exp_sum else "Under-consumption"
        elif dur <= 2:
            etype = "Spike"
        elif np.mean([(h.hour in AFTER_HOURS) or h.dayofweek >= 5 for h in hrs]) >= 0.5:
            etype = "After-hours waste"
        else:
            etype = "Sustained excess"
        ev = {
            "meter": meter, "start": hrs[0], "end": hrs[-1], "hours": dur, "type": etype,
            "actual_kwh": float(y.iloc[sl].sum()), "expected_kwh": exp_sum,
            "excess_kwh": exc, "excess_pct": 100 * exc / exp_sum if exp_sum else np.nan,
            "peak_z": float(z.iloc[sl].abs().max()),
        }
        if tcol:
            ev["temp_c"] = float(weather[tcol].reindex(hrs).mean())
        ev["why"] = explain(ev)
        events.append(ev)
        i = j + 1

    ev = pd.DataFrame(events)
    if len(ev):
        ev = ev.sort_values("excess_kwh", key=lambda x: -x.abs()).reset_index(drop=True)
    return {"resid": resid, "z": z, "sign": sign, "events": ev}


def explain(ev: dict) -> str:
    when = f"{ev['start']:%a %d %b %Y %H:%M} – {ev['end']:%H:%M}" + (
        f" (+{(ev['end'] - ev['start']).days}d)" if (ev['end'] - ev['start']).days else "")
    direction = "above" if ev["excess_kwh"] > 0 else "below"
    t = f" at {ev['temp_c']:.1f} °C" if "temp_c" in ev and not np.isnan(ev.get("temp_c", np.nan)) else ""
    base = (f"{when}: {ev['hours']} h at {abs(ev['excess_pct']):.0f}% {direction} the expected level "
            f"for this hour, weekday and weather{t} "
            f"({ev['actual_kwh']:,.0f} kWh actual vs {ev['expected_kwh']:,.0f} kWh expected, peak z={ev['peak_z']:.1f}).")
    hint = {
        "Spike": " Short burst: check equipment start-up, a fault, or a one-off event.",
        "After-hours waste": " Load stayed high at night or on the weekend: check HVAC, lighting or equipment schedules.",
        "Sustained excess": " Prolonged excess not explained by weather: check setpoints, a stuck control, or added load.",
        "Drop / outage": " Consumption collapsed: possible outage, meter or data fault, or a holiday shutdown.",
        "Under-consumption": " Below normal: a holiday or closure, or a meter under-reading.",
    }[ev["type"]]
    return base + hint
