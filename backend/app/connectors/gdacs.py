"""GDACS RSS → official-layer evidence (points, bbox, alert level, current/ended)."""
from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from datetime import timezone

from ..db import upsert_evidence
from .base import fetch

RSS = "https://www.gdacs.org/xml/rss.xml"
NS = {"gdacs": "http://www.gdacs.org", "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
      "georss": "http://www.georss.org/georss"}
TYPE = {"EQ": "earthquake", "TC": "cyclone", "FL": "flood", "VO": "other", "DR": "drought", "WF": "wildfire",
        "TS": "tsunami"}


def _iso(s):
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def poll() -> list[dict]:
    root = ET.fromstring(fetch(RSS, max_age_s=600))
    out = []
    for it in root.findall(".//item"):
        g = lambda t: (it.findtext(f"gdacs:{t}", namespaces=NS) or "").strip()
        etype, eid = g("eventtype"), g("eventid")
        pt = (it.findtext("georss:point", namespaces=NS) or "").split()
        lat, lon = (float(pt[0]), float(pt[1])) if len(pt) == 2 else (None, None)
        current = g("iscurrent").lower() == "true"
        title, desc = it.findtext("title") or "", it.findtext("description") or ""
        sev = it.find("gdacs:severity", NS)
        q = []
        if sev is not None and sev.get("value"):
            try:
                q.append({"type": {"EQ": "magnitude", "TC": "wind_kmh"}.get(etype, "severity"),
                          "value": float(sev.get("value")), "unit": sev.get("unit")})
            except ValueError:
                pass
        ev = dict(
            evidence_id=f"ev_gdacs_{etype}{eid}_{g('episodeid')}", source_id="src_gdacs", source_name="GDACS",
            source_url=it.findtext("link"), raw_evidence_text=f"{title}\n{desc}",
            evidence_interpretation=f"GDACS {g('alertlevel')} alert: {title}",
            published_at=_iso(it.findtext("pubDate")), valid_from=_iso(g("fromdate")),
            valid_until=None if current else _iso(g("todate")), event_type=TYPE.get(etype, "other"),
            location_text=g("country"), country=g("iso3"), latitude=lat, longitude=lon, bbox=g("bbox"),
            severity=g("alertlevel"), credibility_tier="A", kind="alert", layer="official",
            source_document_id=f"{etype}{eid}", retrieval_method="rss", provenance_status="VALIDATED",
            license_notes="GDACS public feed", event_ref=g("glide") or f"{etype}{eid}", quantities=q, is_synthetic=0,
        )
        upsert_evidence(ev)
        out.append(ev)
    return out
