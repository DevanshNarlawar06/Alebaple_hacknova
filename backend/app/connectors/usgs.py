"""USGS FDSN earthquake events → sensor-layer evidence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

from ..db import upsert_evidence
from .base import fetch

BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query?"


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_evidence(f: dict) -> dict:
    p, (lon, lat, depth) = f["properties"], f["geometry"]["coordinates"]
    t = _iso(p["time"])
    raw = json.dumps({k: p.get(k) for k in ("title", "mag", "magType", "place", "time", "tsunami", "alert",
                                              "status", "url")} | {"lat": lat, "lon": lon, "depth_km": depth},
                     ensure_ascii=False)
    ts = ("USGS lists tsunami-related information for this event (tsunami flag 1)" if p.get("tsunami")
          else "USGS lists no tsunami-related information for this event (tsunami flag 0)")
    interp = (f"USGS: magnitude {p.get('mag')} earthquake, {p.get('place')}, at {t} UTC, depth {depth:.0f} km, "
              f"epicentre {lat:.2f}, {lon:.2f}. {ts}.")
    return dict(
        evidence_id=f"ev_usgs_{f['id']}", source_id="src_usgs", source_name="USGS",
        source_url=p.get("url"), raw_evidence_text=raw, evidence_text=interp, evidence_interpretation=interp,
        published_at=t, valid_from=t, event_type="earthquake", location_text=p.get("place"),
        latitude=lat, longitude=lon, credibility_tier="A", kind="observation", layer="sensor",
        source_document_id=f["id"], retrieval_method="api", provenance_status="VALIDATED",
        license_notes="Public domain", event_ref=f["id"], is_synthetic=0,
        quantities=[{"type": "magnitude", "value": p.get("mag")}, {"type": "depth_km", "value": depth},
                    {"type": "tsunami_flag", "value": p.get("tsunami")}],
    )


def search(start: str, end: str, lat: float | None = None, lon: float | None = None,
           radius_km: float = 1000, minmag: float = 4.0, limit: int = 20) -> list[dict]:
    q = {"format": "geojson", "starttime": start, "endtime": end, "minmagnitude": minmag,
         "orderby": "magnitude", "limit": limit}
    if lat is not None:
        q |= {"latitude": lat, "longitude": lon, "maxradiuskm": radius_km}
    d = json.loads(fetch(BASE + urlencode(q), max_age_s=None if end < "2026" else 600))
    out = []
    for f in d.get("features", []):
        ev = to_evidence(f)
        upsert_evidence(ev)
        out.append(ev)
    return out


def get_event(event_id: str) -> dict:
    d = json.loads(fetch(BASE + urlencode({"format": "geojson", "eventid": event_id}), max_age_s=None))
    ev = to_evidence(d)
    upsert_evidence(ev)
    return ev
