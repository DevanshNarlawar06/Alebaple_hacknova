"""Open-Meteo daily weather at a point → sensor-layer evidence (rain, max temperature, wind)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from ..db import stable_id, upsert_evidence
from .base import FetchError, fetch

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive?"
FORECAST = "https://api.open-meteo.com/v1/forecast?"
DAILY = "precipitation_sum,temperature_2m_max,wind_speed_10m_max"


def daily(lat: float, lon: float, day: str, span_days: int = 1) -> list[dict]:
    """Weather for [day - span_days, day + span_days]. Uses the archive for dates > 5 days old."""
    d = date.fromisoformat(day[:10])
    start, end = d - timedelta(days=span_days), d + timedelta(days=span_days)
    today = datetime.now(timezone.utc).date()
    old = (today - end).days > 5
    q = {"latitude": round(lat, 2), "longitude": round(lon, 2), "daily": DAILY, "timezone": "UTC",
         "start_date": start.isoformat(), "end_date": min(end, today + timedelta(days=7)).isoformat()}
    try:
        data = json.loads(fetch((ARCHIVE if old else FORECAST) + urlencode(q), max_age_s=None if old else 1800))
    except FetchError:
        return []
    dd = data.get("daily", {})
    out = []
    for i, t in enumerate(dd.get("time", [])):
        rain, tmax, wind = (dd.get(k, [None] * 99)[i] for k in ("precipitation_sum", "temperature_2m_max",
                                                                  "wind_speed_10m_max"))
        forecast = (not old) and t >= today.isoformat()
        raw = json.dumps({"date": t, "lat": q["latitude"], "lon": q["longitude"], "precipitation_sum_mm": rain,
                          "temperature_2m_max_c": tmax, "wind_speed_10m_max_kmh": wind,
                          "dataset": "archive (ERA5)" if old else "forecast API"})
        interp = (f"Open-Meteo {'forecast' if forecast else 'recorded'} weather at {q['latitude']}, {q['longitude']} "
                  f"on {t}: rainfall {rain} mm, max temperature {tmax} °C, max wind {wind} km/h.")
        ev = dict(
            evidence_id=stable_id("ev_om_", q["latitude"], q["longitude"], t), source_id="src_openmeteo",
            source_name="Open-Meteo", source_url=(ARCHIVE if old else FORECAST) + urlencode(q),
            raw_evidence_text=raw, evidence_interpretation=interp, evidence_text=interp,
            published_at=f"{t}T23:59:00Z", valid_from=f"{t}T00:00:00Z", valid_until=f"{t}T23:59:59Z",
            event_type="other", latitude=q["latitude"], longitude=q["longitude"], credibility_tier="A",
            kind="observation", layer="sensor", source_document_id=f"openmeteo:{q['latitude']},{q['longitude']}:{t}",
            retrieval_method="api", provenance_status="VALIDATED", license_notes="CC BY 4.0", is_synthetic=0,
            quantities=[{"type": "rainfall_mm", "value": rain, "date": t},
                        {"type": "temp_max_c", "value": tmax, "date": t},
                        {"type": "wind_kmh", "value": wind, "date": t}],
        )
        upsert_evidence(ev)
        out.append(ev)
    return out
