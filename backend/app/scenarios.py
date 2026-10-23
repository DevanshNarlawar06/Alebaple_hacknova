"""Track B demo scenarios (PRD §11.2). Synthetic, India-focused, labelled `is_synthetic=1` everywhere.

Timestamps are relative to the replay start t0, so CURRENT-context checks behave like live data.
Expected statuses are design targets for the demo; they are NOT benchmark ground truth.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .db import stable_id, upsert_evidence


def _t(t0: datetime, minutes: float) -> str:
    return (t0 + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _box(lat, lon, dlat, dlon):
    return {"type": "MultiPolygon", "coordinates": [[[[lon - dlon, lat - dlat], [lon + dlon, lat - dlat],
                                                      [lon + dlon, lat + dlat], [lon - dlon, lat + dlat],
                                                      [lon - dlon, lat - dlat]]]]}


def _ev(sid, t0, **kw):
    base = dict(source_id="src_synthetic", is_synthetic=1, provenance_status="SYNTHETIC", retrieval_method="synthetic",
                credibility_tier="A", license_notes="Synthetic demo data — not a real alert/report")
    base.update(kw)
    base["evidence_id"] = stable_id("ev_syn_", sid, t0.date().isoformat(), kw.get("source_document_id", ""))
    upsert_evidence(base)
    return base


def load_pune_flood(t0: datetime) -> list[dict]:
    """S1 — Pune flash flood: verified, conflicting (dam burst), numeric conflict, partial, multilingual, noise."""
    _ev("pune_alert", t0, source_name="[SYNTHETIC] NDMA-style CAP alert (Pune DDMA)", kind="alert", layer="official",
        raw_evidence_text="Flash flood warning: very heavy rainfall (115+ mm) recorded in Pune city. Waterlogging on "
                          "Sinhagad Road, Vadgaon, Warje and Kothrud. Avoid low-lying roads; move to higher floors.",
        evidence_interpretation="[SYNTHETIC] Severe flash-flood alert for SW Pune (Sinhagad Road, Vadgaon, Warje, Kothrud)",
        event_type="flood", severity="Severe", urgency="Immediate", certainty="Observed", msg_type="Alert",
        published_at=_t(t0, -45), valid_from=_t(t0, -45), valid_until=_t(t0, 360), latitude=18.485, longitude=73.81,
        location_text="Sinhagad Road, Vadgaon, Warje, Kothrud — Pune", country="IN",
        polygon_geojson=_box(18.485, 73.81, 0.035, 0.045), source_document_id="SYN-PUNE-FLOOD-ALERT-1")
    _ev("pune_dam", t0, source_name="[SYNTHETIC] Water Resources Dept notice (Khadakwasla)", kind="alert",
        layer="official", raw_evidence_text="Khadakwasla dam is structurally safe. Controlled discharge of 9,000 cusecs "
                                             "released into Mutha river from 13:00. There is no dam breach. Residents near "
                                             "the riverbed should stay alert.",
        evidence_interpretation="[SYNTHETIC] Official notice: Khadakwasla dam safe, controlled release, no breach",
        event_type="flood", severity="Moderate", msg_type="Alert", published_at=_t(t0, -30), valid_from=_t(t0, -30),
        valid_until=_t(t0, 600), latitude=18.44, longitude=73.77, location_text="Khadakwasla dam, Pune", country="IN",
        source_document_id="SYN-KHADAKWASLA-NOTICE-1")
    _ev("pune_rain", t0, source_name="[SYNTHETIC] Rain gauge (IMD-style AWS, Pune)", kind="observation",
        layer="sensor", raw_evidence_text=json.dumps({"station": "Pune (Shivajinagar) [synthetic]", "rain_24h_mm": 142}),
        evidence_interpretation="[SYNTHETIC] 142 mm rainfall recorded in Pune in the last 24 h (IMD 'very heavy').",
        event_type="flood", published_at=_t(t0, -20), valid_from=_t(t0, -20), valid_until=_t(t0, 1440),
        latitude=18.53, longitude=73.85, location_text="Pune", country="IN", source_document_id="SYN-PUNE-RAIN-1",
        quantities=[{"type": "rainfall_mm", "value": 142, "date": t0.date().isoformat()}])
    _ev("pune_news_local", t0, source_name="[SYNTHETIC] Lokmat-style local news", kind="news", layer="local_news",
        credibility_tier="C", raw_evidence_text="सिंहगड रस्त्यावर पाणी साचले; वडगाव पुलाजवळ वाहने अडकली (Sinhagad Road "
                                                "waterlogged; vehicles stuck near Vadgaon bridge)",
        evidence_interpretation="[SYNTHETIC] Local news: Sinhagad Road waterlogged, vehicles stuck near Vadgaon bridge",
        event_type="flood", published_at=_t(t0, -25), valid_from=_t(t0, -25), latitude=18.47, longitude=73.82,
        location_text="Sinhagad Road, Pune", country="IN", language="mr", source_document_id="SYN-NEWS-LOKMAT-1",
        copy_group_id="cg_syn_pune1", is_group_origin=1)
    _ev("pune_news_copy", t0, source_name="[SYNTHETIC] Aggregator copy", kind="news", layer="national_global",
        credibility_tier="C", raw_evidence_text="Sinhagad Road waterlogged, vehicles stuck near Vadgaon bridge",
        evidence_interpretation="[SYNTHETIC] Copy of the Lokmat-style report",
        event_type="flood", published_at=_t(t0, -10), valid_from=_t(t0, -10), latitude=18.47, longitude=73.82,
        location_text="Sinhagad Road, Pune", country="IN", source_document_id="SYN-NEWS-COPY-1",
        copy_group_id="cg_syn_pune1", is_group_origin=0)
    P = [
        (2, "Sinhagad Road is under 3-4 ft of water, cars stuck near Vadgaon bridge. Avoid the area!",
         "VERIFIED", 18.4745, 73.8180),
        (4, "Khadakwasla dam gates have burst!! Evacuate Pune within 2 hours, forward to everyone", "CONFLICTING",
         18.44, 73.77),
        (6, "पुणे के सिंहगड रोड पर भारी बारिश से पानी भर गया है, गाड़ियाँ फँसी हुई हैं", "VERIFIED", 18.4745, 73.818),
        (8, "300 mm rain fell in Pune today, highest ever recorded", "CONFLICTING", 18.53, 73.85),
        (10, "Flooding in Warje tonight and gangs are looting shops in the area", "UNVERIFIED", 18.4846, 73.8014),
        (11, "Stay safe Pune 🙏 praying for everyone", None, None, None),
        (13, "Water entering homes in Kothrud near Karve Road after the heavy rain", "VERIFIED", 18.503, 73.812),
    ]
    return [dict(offset_min=o, text=x, expected=e, lat=la, lon=lo, scenario="S1 Pune flash flood") for o, x, e, la, lo in P]


def load_delhi_quake(t0: datetime) -> list[dict]:
    """S4 — Delhi earthquake rumour: positive numeric contradiction from a (synthetic) seismic record."""
    _ev("delhi_eq", t0, source_name="[SYNTHETIC] Seismic record (NCS-style)", kind="observation", layer="sensor",
        raw_evidence_text=json.dumps({"mag": 3.1, "place": "6 km NE of New Delhi [synthetic]", "depth_km": 8}),
        evidence_interpretation="[SYNTHETIC] Magnitude 3.1 earthquake 6 km NE of New Delhi, depth 8 km; no damage reported.",
        event_type="earthquake", published_at=_t(t0, -15), valid_from=_t(t0, -15), latitude=28.66, longitude=77.26,
        location_text="New Delhi", country="IN", source_document_id="SYN-DELHI-EQ-1", event_ref="SYN-DELHI-EQ-1",
        quantities=[{"type": "magnitude", "value": 3.1}])
    return [dict(offset_min=15, text="Massive 6.8 magnitude earthquake just hit Delhi, buildings collapsed in Laxmi Nagar",
                 expected="CONFLICTING", lat=28.6304, lon=77.2777, scenario="S4 Delhi quake rumour")]


SCENARIOS = {"pune_flood": load_pune_flood, "delhi_quake": load_delhi_quake}


def build(names: list[str] | None = None, t0: datetime | None = None) -> list[dict]:
    t0 = t0 or datetime.now(timezone.utc)
    posts = []
    for n in names or list(SCENARIOS):
        posts += SCENARIOS[n](t0)
    for p in posts:
        p["posted_at"] = _t(t0, p["offset_min"] - 20)
    return sorted(posts, key=lambda p: p["offset_min"])
