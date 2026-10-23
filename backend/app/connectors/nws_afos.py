"""US NWS text products from the Iowa Environmental Mesonet AFOS archive → official-layer evidence.

Used for historical US benchmark cases (e.g. Guajataca Dam flash-flood emergency, Sep 2017).
Validity windows come from the VTEC string in each product (…/O.NEW.TJSJ.FF.W.0034.170923T1158Z-170923T1500Z/).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urlencode

from ..db import upsert_evidence
from .base import fetch

BASE = "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?"
VTEC = re.compile(r"/O\.(\w{3})\.(\w{4})\.(\w\w)\.(\w)\.(\d{4})\.(\d{6}T\d{4}Z)-(\d{6}T\d{4}Z)/")


def _vtime(s: str) -> str | None:
    if s.startswith("000000"):
        return None
    return datetime.strptime(s, "%y%m%dT%H%MZ").strftime("%Y-%m-%dT%H:%M:%SZ")


ISSUED = re.compile(r"^(\d{3,4}) (AM|PM) ([A-Z]{3}) \w{3} (\w{3}) (\d{1,2}) (\d{4})", re.M)
TZ = {"AST": -4, "EDT": -4, "EST": -5, "CDT": -5, "CST": -6, "MDT": -6, "MST": -7, "PDT": -7, "PST": -8, "UTC": 0}


def _issued(prod: str) -> str | None:
    m = ISSUED.search(prod)
    if not m:
        return None
    hhmm, ap, tz, mon, day, yr = m.groups()
    h, mi = int(hhmm[:-2]), int(hhmm[-2:])
    h = h % 12 + (12 if ap == "PM" else 0)
    from datetime import timedelta
    dt = datetime.strptime(f"{yr} {mon} {day} {h}:{mi}", "%Y %b %d %H:%M") - timedelta(hours=TZ.get(tz, 0))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def products(pil: str, sdate: str, edate: str, limit: int = 20, keyword: str | None = None) -> list[dict]:
    url = BASE + urlencode({"pil": pil, "sdate": sdate, "edate": edate, "limit": limit, "fmt": "text"})
    text = fetch(url, max_age_s=None).decode("utf-8", "replace")
    out = []
    for prod in [p.strip() for p in re.split(r"\x01|\n\$\$\s*\n", text) if len(p.strip()) > 200]:
        if keyword and keyword.lower() not in prod.lower():
            continue
        m = VTEC.search(prod)
        start = (_vtime(m.group(6)) if m else None)
        issued = _issued(prod) or start
        end = _vtime(m.group(7)) if m else None
        action = m.group(1) if m else None
        head = next((ln for ln in prod.splitlines() if ln.startswith("...") or "EMERGENCY" in ln), "")
        h = hashlib.sha1(prod.encode()).hexdigest()[:12]
        ev = dict(
            evidence_id=f"ev_nws_{pil}_{h}", source_id="src_nws", source_name="NWS (IEM AFOS archive)",
            source_url=url, raw_evidence_text=prod,
            evidence_interpretation=f"NWS {pil} product, VTEC action {action}, valid {start} → {end}. {head.strip('. ')}",
            published_at=issued, valid_from=start or issued, valid_until=end, msg_type=action,
            event_type="flood", credibility_tier="A", kind="alert", layer="official",
            source_document_id=f"{pil}:{m.group(0) if m else h}", retrieval_method="archive",
            provenance_status="VALIDATED", license_notes="US Government work, public domain", is_synthetic=0,
        )
        upsert_evidence(ev)
        out.append(ev)
    return out
