"""NDMA SACHET CAP feed → official-layer evidence with polygons and validity windows."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from shapely.geometry import Polygon

from ..db import upsert_evidence
from .base import FetchError, fetch

RSS = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
CAP = "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={}"
POLY = "https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile?identifier={}"
NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

EVENT_MAP = {"flood": "flood", "rain": "flood", "heavy rain": "flood", "flash flood": "flood",
             "cyclone": "cyclone", "storm": "storm", "thunderstorm": "storm", "lightning": "storm",
             "earthquake": "earthquake", "tsunami": "tsunami", "landslide": "landslide",
             "heat": "heatwave", "heat wave": "heatwave", "cold wave": "other", "fire": "wildfire",
             "avalanche": "landslide", "drought": "drought"}


def _hazard(ev: str) -> str:
    e = (ev or "").lower()
    for k, v in EVENT_MAP.items():
        if k in e:
            return v
    return "other"


def _iso(s: str | None) -> str | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return s


def _t(node, tag):
    x = node.find(f"cap:{tag}", NS)
    return x.text.strip() if x is not None and x.text else None


def parse_polygon(ident: str):
    try:
        root = ET.fromstring(fetch(POLY.format(ident), max_age_s=None))
    except (FetchError, ET.ParseError):
        return None
    polys = []
    for p in root.iter("polygon"):
        pts = []
        for pair in (p.text or "").split():
            try:
                la, lo = map(float, pair.split(","))
                pts.append((lo, la))
            except ValueError:
                pass
        if len(pts) >= 3:
            polys.append(pts)
    return polys or None


def fetch_alert(ident: str) -> dict | None:
    root = ET.fromstring(fetch(CAP.format(ident), max_age_s=None))
    infos = root.findall("cap:info", NS)
    info = next((i for i in infos if (_t(i, "language") or "").lower().startswith("en")), infos[0] if infos else None)
    if info is None:
        return None
    others = [(_t(i, "language"), _t(i, "headline")) for i in infos if i is not info]
    area = info.find("cap:area", NS)
    area_desc = _t(area, "areaDesc") if area is not None else None
    polys = parse_polygon(ident)
    lat = lon = None
    geo = None
    if polys:
        shapes = [Polygon(p) for p in polys]
        biggest = max(shapes, key=lambda s: s.area)
        c = biggest.representative_point()
        lat, lon = c.y, c.x
        geo = {"type": "MultiPolygon", "coordinates": [[list(map(list, p))] for p in polys]}
    geo_note = "polygon"
    if lat is None:
        # No polygon available: fall back to the issuing state (region precision), never a made-up point
        from .geocode import geocode
        sender_txt = (_t(root, "sender") or "").replace("-SDMA", "").replace("SDMA", "").replace("-", " ").strip()
        g = geocode(f"{sender_txt}, India") if sender_txt and "NDMA" not in sender_txt.upper() else {"unresolved": True}
        if not g.get("unresolved"):
            lat, lon, geo_note = g["lat"], g["lon"], "issuing state (region precision)"
        else:
            geo_note = "unresolved"
    headline, desc, instr = _t(info, "headline"), _t(info, "description"), _t(info, "instruction")
    sender = _t(root, "sender")
    raw = "\n".join(x for x in [headline, desc, f"Instruction: {instr}" if instr else None,
                                 f"Area: {area_desc}" if area_desc else None] if x)
    event = _t(info, "event")
    refs = _t(root, "references")
    return dict(
        evidence_id=f"ev_ndma_{ident}", source_id="src_ndma", source_name=f"NDMA SACHET ({sender})",
        source_url=CAP.format(ident), raw_evidence_text=raw,
        evidence_interpretation=f"Official {(_t(info,'severity') or '').lower()} {event} alert from {sender}"
                                f" valid {_t(info,'effective')} → {_t(info,'expires')}: {headline}",
        published_at=_iso(_t(root, "sent")), valid_from=_iso(_t(info, "effective")),
        valid_until=_iso(_t(info, "expires")), msg_type=_t(root, "msgType"),
        severity=_t(info, "severity"), urgency=_t(info, "urgency"), certainty=_t(info, "certainty"),
        event_type=_hazard(event), location_text=area_desc, latitude=lat, longitude=lon, country="IN",
        polygon_geojson=geo, credibility_tier="A", kind="alert", layer="official",
        source_document_id=_t(root, "identifier"), retrieval_method="rss", provenance_status="VALIDATED",
        license_notes="Public government alert", language="en", is_synthetic=0,
        event_ref=refs, quantities=[{"type": "geo_basis", "value": geo_note}], region=json.dumps(others, ensure_ascii=False)[:2000] if others else None,
    )


def poll(limit: int = 40) -> list[dict]:
    root = ET.fromstring(fetch(RSS, max_age_s=120))
    out = []
    for it in root.findall(".//item")[:limit]:
        ident = (it.findtext("guid") or "").strip()
        if not ident:
            continue
        try:
            ev = fetch_alert(ident)
        except (FetchError, ET.ParseError):
            continue
        if ev:
            upsert_evidence(ev)
            out.append(ev)
    return out
