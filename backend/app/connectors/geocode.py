"""Geocoding with Nominatim + shared cache. Never invents coordinates.

Rejects results that are businesses/amenities for region-level text (the handover's 'USA Nails' bug),
returns a precision level, and reports unresolved/ambiguous places instead of guessing.
"""
from __future__ import annotations

import json
import threading
from urllib.parse import urlencode

from ..config import GEOCODE_CACHE
from ..db import now
from .base import FetchError, fetch

_lock = threading.Lock()
OK_CLASSES = {"place", "boundary", "natural", "waterway", "highway", "landuse", "man_made", "leisure", "amenity_landmark"}
PRECISION = {"country": "country", "state": "region", "region": "region", "state_district": "region",
             "county": "region", "province": "region", "city": "city", "town": "city", "municipality": "city",
             "village": "city", "suburb": "neighbourhood", "neighbourhood": "neighbourhood", "quarter": "neighbourhood",
             "road": "street", "hamlet": "neighbourhood", "city_district": "neighbourhood", "district": "region"}


def _load():
    try:
        return json.loads(GEOCODE_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def geocode(text: str, country_codes: str | None = None) -> dict:
    """Return {lat, lon, precision, display, confidence} or {unresolved: True, reason}."""
    if not text or not text.strip():
        return {"unresolved": True, "reason": "no place mentioned"}
    if "/" in text:
        return {"unresolved": True, "reason": f"composite place '{text}' (several regions)"}
    key = f"v2|{text.strip().lower()}|{country_codes or ''}"
    with _lock:
        cache = _load()
    if key in cache:
        return cache[key]
    q = {"q": text, "format": "jsonv2", "limit": 3, "addressdetails": 0}
    if country_codes:
        q["countrycodes"] = country_codes
    try:
        res = json.loads(fetch("https://nominatim.openstreetmap.org/search?" + urlencode(q), max_age_s=None))
    except FetchError as e:
        return {"unresolved": True, "reason": f"geocoder unavailable ({e})"}
    good = [r for r in res if r.get("category", r.get("class")) in OK_CLASSES]
    if not good:
        out = {"unresolved": True, "reason": f"no place-level match for '{text}'"}
    else:
        r = good[0]
        prec = PRECISION.get(r.get("addresstype") or r.get("type"), "approximate")
        ambiguous = len(good) > 1 and good[1].get("importance", 0) > 0.8 * r.get("importance", 1) and \
            abs(float(good[1]["lat"]) - float(r["lat"])) + abs(float(good[1]["lon"]) - float(r["lon"])) > 1
        out = {"lat": float(r["lat"]), "lon": float(r["lon"]), "precision": prec, "display": r.get("display_name"),
               "confidence": 0.5 if ambiguous else 0.85, "ambiguous": ambiguous, "queried_at": now()}
    with _lock:
        cache = _load()
        cache[key] = out
        GEOCODE_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
