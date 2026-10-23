"""Load energy CSVs into one hourly frame: meters in kWh per hour, plus weather columns."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

WEATHER_PAT = re.compile(
    r"temp|^t_out$|humid|^rh_out$|wind|press|visib|dew|diffuse|irrad|solar|weather", re.I
)


@dataclass
class EnergyData:
    name: str
    meters: pd.DataFrame          # hourly kWh, one column per meter
    weather: pd.DataFrame         # hourly weather (temperature first if present)
    source: str = ""
    synthetic: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def temp_col(self) -> str | None:
        for c in self.weather.columns:
            if "temp" in c.lower():
                return c
        return None


def _find_time_col(df: pd.DataFrame) -> str:
    best, best_ok = None, 0.0
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        sample = df[c].dropna().astype(str).head(500)
        ok = pd.to_datetime(sample, errors="coerce").notna().mean()
        if ok > best_ok:
            best, best_ok = c, ok
    if best is None or best_ok < 0.9:
        raise ValueError("No timestamp column found (need a column of dates/times).")
    return best


def detect_columns(df: pd.DataFrame) -> tuple[str, list[str], list[str]]:
    """Return (time column, meter columns, weather columns) guesses."""
    tcol = _find_time_col(df)
    num = [c for c in df.columns if c != tcol and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.9]
    weather = [c for c in num if WEATHER_PAT.search(c.strip())]
    meters = [c for c in num if c not in weather and not re.fullmatch(r"rv\d|id|index", c.strip(), re.I)]
    return tcol, meters, weather


def to_hourly(
    df: pd.DataFrame,
    tcol: str,
    meters: list[str],
    weather: list[str],
    unit: str = "kW",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """unit: 'kW' / 'W' (average power readings) or 'kWh' / 'Wh' (energy per interval)."""
    d = df.copy()
    d[tcol] = pd.to_datetime(d[tcol], errors="coerce")
    d = d.dropna(subset=[tcol]).sort_values(tcol).drop_duplicates(tcol).set_index(tcol)
    for c in meters + weather:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    m = d[meters]
    if unit in ("kW", "W"):
        hourly = m.resample("h").mean()           # mean power over the hour = energy in the hour
    else:
        hourly = m.resample("h").sum(min_count=1)  # energy per interval -> sum
    if unit in ("W", "Wh"):
        hourly = hourly / 1000.0
    hourly.columns = [c.strip() for c in meters]

    w = d[weather].resample("h").mean() if weather else pd.DataFrame(index=hourly.index)
    w.columns = [c.strip() for c in weather]
    hourly = hourly.interpolate(limit=3)
    w = w.reindex(hourly.index).interpolate(limit=6).ffill().bfill()
    return hourly, w


def load_csv(path_or_buf, name: str, unit: str = "kW", meters=None, weather=None,
             rename: dict | None = None, source: str = "", synthetic: bool = False) -> EnergyData:
    df = pd.read_csv(path_or_buf)
    df.columns = [str(c) for c in df.columns]
    tcol, m_guess, w_guess = detect_columns(df)
    meters = meters or m_guess
    weather = weather if weather is not None else w_guess
    hourly, w = to_hourly(df, tcol, meters, weather, unit)
    if rename:
        hourly = hourly.rename(columns=rename)
        w = w.rename(columns=rename)
    return EnergyData(name, hourly, w, source=source, synthetic=synthetic)


# ---------- bundled datasets ----------

def load_tetouan() -> EnergyData:
    return load_csv(
        DATA_DIR / "raw" / "tetouan.csv", "Tetouan City (3 distribution zones)", unit="kW",
        meters=["Zone 1 Power Consumption", "Zone 2  Power Consumption", "Zone 3  Power Consumption"],
        weather=["Temperature", "Humidity", "Wind Speed"],
        rename={"Zone 1 Power Consumption": "Zone 1", "Zone 2  Power Consumption": "Zone 2",
                "Zone 3  Power Consumption": "Zone 3", "Temperature": "Temperature (°C)",
                "Humidity": "Humidity (%)", "Wind Speed": "Wind speed"},
        source="UCI #849 Power Consumption of Tetouan City (2017, 10-min, CC BY 4.0)",
    )


def load_appliances() -> EnergyData:
    return load_csv(
        DATA_DIR / "raw" / "appliances.csv", "Low-energy house (UCI Appliances)", unit="Wh",
        meters=["Appliances", "lights"], weather=["T_out", "RH_out", "Windspeed"],
        rename={"lights": "Lights", "T_out": "Temperature (°C)", "RH_out": "Humidity (%)",
                "Windspeed": "Wind speed"},
        source="UCI #374 Appliances Energy Prediction (2016, 10-min, CC BY 4.0)",
    )


def load_campus() -> EnergyData:
    p = DATA_DIR / "synthetic" / "campus_hourly.csv"
    if not p.exists():
        from scripts.make_campus import main as make  # lazy: generate on first use
        make()
    df = pd.read_csv(p, parse_dates=["timestamp"]).set_index("timestamp")
    wcols = [c for c in df.columns if WEATHER_PAT.search(c)]
    return EnergyData("Synthetic campus (5 buildings)", df.drop(columns=wcols), df[wcols],
                      source="Synthetic, generated by scripts/make_campus.py with hidden injected waste; "
                             "weather = real Pune 2025 hourly temperature (Open-Meteo) when available",
                      synthetic=True)


DATASETS = {
    "Tetouan City — 3 zones (UCI, real)": load_tetouan,
    "Smart campus — 5 buildings (synthetic)": load_campus,
    "Household — appliances (UCI, real)": load_appliances,
}
