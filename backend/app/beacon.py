"""Beacon threat level for a location (PRD FR-10).

RED (alert): an active official alert covers the location (polygon or within radius) with severity
Severe/Extreme, OR a VERIFIED current claim within radius. Social reports alone never raise RED.
YELLOW (watch): an active official alert of lower severity nearby, or ≥ 2 UNVERIFIED/PARTIALLY_SUPPORTED claims nearby.
GREEN (all clear): otherwise. Rumour cards: CONFLICTING / OUTDATED claims within 50 km.
"""
from __future__ import annotations

import json
import math

from shapely.geometry import Point, shape

from .db import now, rows


def _hav(a, b, c, d):
    a, b, c, d = map(math.radians, (a, b, c, d))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2))


def threat_for(lat: float, lon: float, radius_km: float = 10) -> dict:
    t = now()
    alerts = rows("SELECT evidence_id, source_name, event_type, severity, urgency, raw_evidence_text, valid_until, "
                  "latitude, longitude, polygon_geojson, is_synthetic, source_url FROM evidence WHERE kind='alert' "
                  "AND valid_from <= ? AND (valid_until IS NULL OR valid_until >= ?) AND source_id IN ('src_ndma','src_gdacs','src_synthetic')",
                  (t, t))
    covering, nearby = [], []
    for a in alerts:
        inside = False
        if a["polygon_geojson"]:
            try:
                inside = shape(json.loads(a["polygon_geojson"])).buffer(0.01).contains(Point(lon, lat))
            except Exception:
                pass
        d = _hav(lat, lon, a["latitude"], a["longitude"]) if a["latitude"] is not None else None
        a["distance_km"] = round(d, 1) if d is not None else None
        a.pop("polygon_geojson", None)
        if inside or (d is not None and d <= radius_km):
            covering.append(a)
        elif d is not None and d <= radius_km * 5:
            nearby.append(a)
    claims = rows("""SELECT c.claim_id, c.claim_text, c.latitude, c.longitude, v.status, v.subtype, v.confidence, v.created_at
                     FROM verdicts v JOIN claims c ON c.claim_id=v.claim_id WHERE v.verification_context='CURRENT'
                     AND v.version=(SELECT MAX(version) FROM verdicts v2 WHERE v2.claim_id=v.claim_id AND v2.verification_context='CURRENT')
                     AND c.latitude IS NOT NULL""")
    near = []
    for c in claims:
        d = _hav(lat, lon, c["latitude"], c["longitude"])
        if d <= 50:
            near.append(c | {"distance_km": round(d, 1)})
    near.sort(key=lambda c: c["distance_km"])
    severe = [a for a in covering if (a["severity"] or "").lower() in ("severe", "extreme", "red", "orange")]
    verified_close = [c for c in near if c["status"] == "VERIFIED" and c["distance_km"] <= radius_km]
    unverified_close = [c for c in near if c["status"] == "UNVERIFIED" and c["distance_km"] <= radius_km]
    if severe or verified_close:
        level = "RED"
        reason = (f"Official alert covers your area: {severe[0]['source_name']}" if severe
                  else "A verified report within your area")
    elif covering or nearby or len(unverified_close) >= 2:
        level = "YELLOW"
        reason = ("Official advisory nearby" if (covering or nearby)
                  else "Several unconfirmed reports nearby — not confirmed by officials yet")
    else:
        level, reason = "GREEN", "No verified threats near you"
    rumours = [c for c in near if c["status"] in ("CONFLICTING", "OUTDATED")][:5]
    return {"level": level, "reason": reason, "updated_at": t, "alerts_covering": covering[:5],
            "alerts_nearby": nearby[:5], "nearby_claims": near[:10], "rumour_checks": rumours,
            "rule": "RED only on official alerts or verified claims; social reports alone cap at YELLOW"}
