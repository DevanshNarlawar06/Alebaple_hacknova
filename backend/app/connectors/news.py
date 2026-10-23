"""News connectors: Google News RSS search (local + national, multilingual) and YouTube channel RSS.

Only headlines, publisher, time and link are stored (no full-text copying). Near-identical headlines are
grouped (copied-source rule, PRD FR-4): only the earliest publisher in a group counts as independent.
"""
from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from datetime import timezone
from urllib.parse import quote_plus

from rapidfuzz import fuzz

from ..db import stable_id, upsert_evidence
from .base import FetchError, fetch

NATIONAL = {"ndtv", "times of india", "the hindu", "hindustan times", "indian express", "india today", "dd news",
            "the economic times", "reuters", "associated press", "ap news", "bbc", "cnn", "the guardian",
            "al jazeera", "new york times", "washington post", "aaj tak", "abp news", "news18", "zee news",
            "republic", "mint", "firstpost", "the print", "scroll", "un news", "reliefweb", "wion"}
EDITIONS = {"en": ("en-IN", "IN", "IN:en"), "hi": ("hi", "IN", "IN:hi"), "mr": ("mr", "IN", "IN:mr"),
            "en-US": ("en-US", "US", "US:en")}


def _iso(s):
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


import re as _re
_NUM = {"dozens": 24, "hundreds": 200, "thousands": 2000}
_DEATHS = _re.compile(r"(?:(?:at least|more than|over|nearly|about|around|toll (?:rises|climbs|jumps|reaches|hits) to|toll at)\s+)?"
                      r"([\d,]{1,7}|dozens|hundreds|thousands)\s+(?:people\s+|persons\s+)?(?:(?:were|have been|are|feared)\s+)?(?:dead|killed|deaths|die|died|lives)", _re.I)
_TOLL = _re.compile(r"death toll[^\d]{0,25}([\d,]{1,7})", _re.I)


def parse_quantities(title: str) -> list[dict]:
    m = _TOLL.search(title) or _DEATHS.search(title)
    if not m:
        return []
    raw = m.group(1).lower().replace(",", "")
    v = _NUM.get(raw) or (int(raw) if raw.isdigit() else None)
    return [{"type": "deaths", "value": v, "approx": not raw.isdigit()}] if v else []


def layer_for(publisher: str) -> str:
    p = (publisher or "").lower()
    return "national_global" if any(n in p for n in NATIONAL) else "local_news"


def google_news(query: str, lang: str = "en", after: str | None = None, before: str | None = None,
                hazard: str = "unknown", limit: int = 15) -> list[dict]:
    q = query + (f" after:{after}" if after else "") + (f" before:{before}" if before else "")
    hl, gl, ceid = EDITIONS.get(lang, EDITIONS["en"])
    url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl={hl}&gl={gl}&ceid={ceid}"
    try:
        root = ET.fromstring(fetch(url, max_age_s=None if before and before < "2026" else 900))
    except (FetchError, ET.ParseError):
        return []
    items = []
    for it in root.findall(".//item")[:limit]:
        title = (it.findtext("title") or "").strip()
        pub = (it.findtext("source") or "").strip()
        if pub and title.endswith(" - " + pub):
            title = title[: -len(pub) - 3]
        items.append(dict(title=title, publisher=pub, link=it.findtext("link"), published=_iso(it.findtext("pubDate"))))
    items.sort(key=lambda x: x["published"] or "9999")
    groups: list[list[dict]] = []
    for x in items:
        for g in groups:
            if fuzz.token_set_ratio(x["title"], g[0]["title"]) >= 88:
                g.append(x)
                break
        else:
            groups.append([x])
    out = []
    for g in groups:
        origin = g[0]
        gid = stable_id("cg_", origin["title"])
        for i, x in enumerate(g):
            ev = dict(
                evidence_id=stable_id("ev_news_", x["link"]), source_id="src_google_news",
                source_name=x["publisher"] or "Google News", source_url=x["link"],
                raw_evidence_text=x["title"], evidence_interpretation=f"{x['publisher']}: {x['title']}",
                published_at=x["published"], valid_from=x["published"], event_type=hazard, credibility_tier="C",
                kind="news", layer=layer_for(x["publisher"]), source_document_id=x["link"],
                retrieval_method="rss", provenance_status="VALIDATED", license_notes="Headline + link only",
                language=lang[:2], quantities=parse_quantities(x["title"]), copy_group_id=gid, is_group_origin=1 if i == 0 else 0, is_synthetic=0,
            )
            upsert_evidence(ev)
            out.append(ev)
    return out


def youtube_channel(channel_id: str, channel_name: str, layer: str = "local_news", hazard: str = "unknown") -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    ns = {"a": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
    try:
        root = ET.fromstring(fetch(url, max_age_s=600))
    except (FetchError, ET.ParseError):
        return []
    out = []
    for e in root.findall("a:entry", ns):
        title = e.findtext("a:title", namespaces=ns) or ""
        link = e.find("a:link", ns).get("href") if e.find("a:link", ns) is not None else None
        desc = e.findtext("media:group/media:description", namespaces=ns) or ""
        pub = e.findtext("a:published", namespaces=ns)
        ev = dict(evidence_id=stable_id("ev_yt_", link), source_id="src_youtube", source_name=channel_name,
                  source_url=link, raw_evidence_text=f"{title}\n{desc[:500]}",
                  evidence_interpretation=f"{channel_name} (video): {title}", published_at=pub, valid_from=pub,
                  event_type=hazard, credibility_tier="C", kind="news", layer=layer, source_document_id=link,
                  retrieval_method="rss", provenance_status="VALIDATED", license_notes="Metadata only", is_synthetic=0)
        upsert_evidence(ev)
        out.append(ev)
    return out
