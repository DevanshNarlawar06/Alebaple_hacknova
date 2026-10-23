"""SachVerify verification agent: a bounded, traced state graph (PRD §7, §8).

extract → triage → geocode → gather (DB + live tools, by hazard) → bind_event → stance per (fact, evidence)
→ validity per context → proposition states → claim status (rule table) → explanation → persist.

Epistemic rule: absence of evidence is never contradiction. CONFLICTING needs positive contradicting evidence.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone

import numpy as np
from shapely.geometry import Point, shape

from .. import config as C
from ..connectors import geocode as geo_mod
from ..connectors import news, openmeteo, usgs
from ..connectors.base import FetchError
from ..db import conn, insert, new_id, now, rows
from ..ml import models
from .extract import extract

COMPAT = {"flood": {"flood", "storm", "cyclone", "other"}, "storm": {"storm", "cyclone", "flood", "other"},
          "cyclone": {"cyclone", "storm", "flood", "other"}, "earthquake": {"earthquake", "tsunami"},
          "tsunami": {"earthquake", "tsunami"}, "landslide": {"landslide", "flood", "storm", "other"},
          "heatwave": {"heatwave", "other"}, "wildfire": {"wildfire", "other"}, "drought": {"drought", "other"},
          "other": {"other", "flood", "storm"}, "unknown": set(C.HAZARDS)}


# ---------------- helpers ----------------

def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def haversine(a, b, c, d) -> float:
    a, b, c, d = map(math.radians, (a, b, c, d))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2))


def _q(ev: dict, qtype: str):
    try:
        qs = json.loads(ev.get("quantities") or "[]") if isinstance(ev.get("quantities"), str) else (ev.get("quantities") or [])
    except json.JSONDecodeError:
        qs = []
    return [q for q in qs if q.get("type") == qtype and q.get("value") is not None]


def _trust(ev: dict) -> float:
    t = C.LAYER_TRUST.get(ev.get("layer") or "", None)
    if t is None:
        t = C.TIER_TRUST.get(ev.get("credibility_tier") or "D", 0.25)
    if ev.get("provenance_status") == "PROVISIONAL":
        t = min(t, 0.7)
    return t


# ---------------- evidence gathering ----------------

def gather(hazard: str, lat, lon, place_words: list[str], event_day: datetime, t_verify: datetime,
           lang: str, place_query: str | None, live: bool, trace: list, prop_queries: list[str] | None = None,
           scope: str | None = None) -> list[dict]:
    R = C.HAZARD_GEO.get(hazard, (30, 150))[1]
    calls = []
    fetched: set[str] = set()
    tt = time.time()
    if live:
        d0, d1 = (event_day - timedelta(days=3)).date().isoformat(), (event_day + timedelta(days=3)).date().isoformat()
        try:
            if hazard in ("earthquake", "tsunami"):
                got = usgs.search(d0, d1, lat, lon, 1500, 4.5) if lat is not None else usgs.search(d0, d1, minmag=6)
                calls.append(f"usgs.search({d0}..{d1}) → {len(got)}")
            if lat is not None and hazard in ("flood", "storm", "cyclone", "heatwave", "landslide", "other", "unknown"):
                got = openmeteo.daily(lat, lon, event_day.date().isoformat(), 1)
                calls.append(f"openmeteo.daily({lat:.2f},{lon:.2f},{event_day.date()}) → {len(got)}")
            if place_query:
                place = place_query.split(",")[0]
                old = (t_verify - event_day).days > 7
                hz_word = {"unknown": "disaster", "other": "disaster"}.get(hazard, hazard)
                kw = dict(after=(event_day - timedelta(days=1)).date().isoformat(),
                          before=(event_day + timedelta(days=8)).date().isoformat()) if old else {}
                ed = "en" if (lat is not None and -10 < lat < 40 and 60 < (lon or 0) < 100) else "en-US"
                got = news.google_news(f"{place} {hz_word}" + ("" if old else " when:3d"), ed, hazard=hazard, **kw)
                fetched |= {g["evidence_id"] for g in got}
                calls.append(f"news.google_news('{place} {hz_word}', {ed}) → {len(got)}")
                for pq in (prop_queries or [])[:3]:
                    got = news.google_news(pq + ("" if old else " when:3d"), ed, hazard=hazard, **kw)
                    fetched |= {g["evidence_id"] for g in got}
                    calls.append(f"news.google_news(fact: '{pq[:50]}') → {len(got)}")
                if lang in ("hi", "mr"):
                    got = news.google_news(f"{place} {hz_word}" + ("" if old else " when:3d"), lang, hazard=hazard, **kw)
                    fetched |= {g["evidence_id"] for g in got}
                    calls.append(f"news.google_news(lang={lang}) → {len(got)}")
        except FetchError as e:
            calls.append(f"live tool failed: {e}")
    trace.append({"step": "gather.live", "calls": calls, "secs": round(time.time() - tt, 1)})

    lo = _iso(event_day - timedelta(days=10))
    hi = _iso(t_verify + timedelta(hours=1))
    cand = rows("SELECT * FROM evidence WHERE (published_at IS NULL OR published_at BETWEEN ? AND ?) "
                "AND (event_type IN ({}) OR kind IN ('observation','news'))".format(
                    ",".join("?" * len(COMPAT.get(hazard, {hazard})))),
                (lo, hi, *COMPAT.get(hazard, {hazard})))
    if scope == "synthetic":  # demo scenarios are judged only against their own synthetic evidence
        cand = [e for e in cand if e.get("is_synthetic")]
    out = []
    pw = [w.lower() for w in place_words if len(w) >= 4]
    for ev in cand:
        g, dist, basis = None, None, None
        if ev.get("polygon_geojson") and lat is not None:
            try:
                if shape(json.loads(ev["polygon_geojson"])).buffer(0.02).contains(Point(lon, lat)):
                    g, dist, basis = 1.0, 0.0, "inside alert area"
            except Exception:
                pass
        if g is None and ev.get("kind") == "news" and ev.get("latitude") is None:
            pass  # handled by the text/place match below
        elif g is None and ev.get("latitude") is not None and lat is not None:
            dist = haversine(lat, lon, ev["latitude"], ev["longitude"])
            if dist > R:
                continue
            D = C.HAZARD_GEO.get(hazard, (30, 150))[0]
            g, basis = math.exp(-dist / D) if dist > D * 0.2 else 1.0, f"{dist:.0f} km away"
        if g is None:
            txt = (ev.get("raw_evidence_text") or "").lower() + " " + (ev.get("evidence_interpretation") or "").lower()
            hits = [w for w in pw if w in txt]
            if hits:
                g, basis = 0.9, f"mentions '{hits[0]}'"
            elif ev["evidence_id"] in fetched:
                g, basis = 0.6, "returned by this claim's place-specific news search"
            else:
                continue
        ev["_geo"], ev["_dist"], ev["_geo_basis"] = g, dist, basis
        out.append(ev)
    trace.append({"step": "gather.candidates", "n": len(out)})
    return out


def bind_event(hazard, lat, lon, event_day, cands, trace) -> tuple[str | None, list[dict]]:
    """Pick the single real event the claim refers to; drop evidence about other events of the same kind."""
    evs = [e for e in cands if e.get("event_ref") and e.get("kind") in ("observation", "alert") and
           e.get("source_id") in ("src_usgs", "src_gdacs")]
    if not evs:
        return None, cands
    def score(e):
        dd = abs((_dt(e.get("valid_from") or e.get("published_at")) or event_day) - event_day).total_seconds() / 86400
        dk = e["_dist"] if e.get("_dist") is not None else 300
        return dd / 2 + dk / 300
    evs.sort(key=score)
    bound = evs[0]["event_ref"]
    drop = {e["evidence_id"] for e in evs if e["event_ref"] != bound and e.get("source_id") == evs[0].get("source_id")}
    for e in cands:
        if e.get("event_ref") == bound:
            e["_geo"], e["_geo_basis"] = 1.0, f"the event this claim refers to ({bound})"
    trace.append({"step": "bind_event", "bound": bound, "candidates": [(e["event_ref"], round(score(e), 2)) for e in evs[:5]],
                  "excluded_other_events": sorted(drop)})
    return bound, [e for e in cands if e["evidence_id"] not in drop]


# ---------------- stance ----------------

def rule_stance(p: dict, ev: dict, hazard: str, event_day: datetime, claim_time: datetime) -> dict | None:
    txt = (p["text_en"] or "").lower()
    qt, qv = p.get("quantity_type"), p.get("quantity_value")
    if qt == "magnitude" and qv:
        for q in _q(ev, "magnitude"):
            diff = abs(float(q["value"]) - qv)
            if diff <= 0.35:
                return {"ent": 0.9, "con": 0.0, "rule": f"magnitude {qv} matches recorded M{q['value']}"}
            if diff >= 0.9:
                return {"ent": 0.0, "con": 0.9, "rule": f"claimed magnitude {qv} vs recorded M{q['value']}", "kind": "NUMERIC_CONFLICT"}
    if ("tsunami" in txt or "wave" in txt) and _q(ev, "tsunami_flag"):
        flag = _q(ev, "tsunami_flag")[0]["value"]
        if flag == 0:
            return {"ent": 0.0, "con": 0.75, "kind": "POSITIVE_CONTRADICTION",
                    "rule": "the bound earthquake record lists no tsunami-related information (tsunami flag 0)"}
        return {"ent": 0.55, "con": 0.0, "rule": "the bound earthquake record lists tsunami-related information"}
    rain = _q(ev, "rainfall_mm")
    if rain and hazard in ("flood", "storm", "cyclone", "landslide", "unknown", "other"):
        day = rain[0].get("date")
        if day and abs((datetime.fromisoformat(day).replace(tzinfo=timezone.utc) - event_day.replace(hour=0, minute=0, second=0, microsecond=0)).days) <= 1:
            mm = float(rain[0]["value"])
            if qt == "rainfall_mm" and qv:
                r = qv / max(mm, 0.1)
                if 0.6 <= r <= 1.6:
                    return {"ent": 0.8, "con": 0.0, "rule": f"claimed {qv} mm vs recorded {mm} mm"}
                if r > 2.5 and mm < qv:
                    return {"ent": 0.0, "con": 0.8, "kind": "NUMERIC_CONFLICT", "rule": f"claimed {qv} mm vs recorded {mm} mm"}
            elif p.get("type") == "event" and any(w in txt for w in ("rain", "flood", "waterlog", "inundat", "submerge")):
                if mm >= 64.5:
                    return {"ent": 0.75, "con": 0.0, "rule": f"{mm} mm rain recorded (IMD 'heavy' ≥ 64.5 mm)"}
                if mm >= 15.6:
                    return {"ent": 0.4, "con": 0.0, "rule": f"{mm} mm rain recorded (moderate)"}
                if mm < 1.0 and "rain" in txt:
                    return {"ent": 0.0, "con": 0.5, "kind": "NUMERIC_CONFLICT", "rule": f"only {mm} mm rain recorded that day"}
                return {"ent": 0.0, "con": 0.0, "rule": f"{mm} mm rain recorded (not decisive)"}
    if p.get("type") == "directive" and ev.get("kind") == "alert":
        raw = (ev.get("raw_evidence_text") or "").lower()
        if any(k in raw for k in ("evacuat", "higher ground", "move to", "leave the area", "shelter")):
            return {"ent": 0.8, "con": 0.0, "rule": "official alert issues the same protective directive"}
    if qt in ("deaths", "injured", "evacuated", "missing", "affected") and qv:
        for q in _q(ev, qt):
            v = float(q["value"])
            pub = _dt(ev.get("published_at")) or claim_time
            if abs(v - qv) <= 0.2 * max(v, qv) and pub <= claim_time + timedelta(hours=24):
                return {"ent": 0.8, "con": 0.0, "rule": f"{qt} {qv:g} matches contemporaneous report of {v:g}"}
            if pub > claim_time and v != qv:
                return {"ent": 0.0, "con": 0.0, "superseding": True, "rule": f"later report revised {qt} to {v:g}"}
            # earlier/contemporaneous different counts are expected while tolls evolve: not a contradiction
            return {"ent": 0.0, "con": 0.0, "rule": f"other report gave {qt} {v:g} (evolving count; not decisive)"}
        if ev.get("kind") == "news":
            return {"ent": 0.0, "con": 0.0, "rule": "no count in this item (count claims are not judged by text similarity)"}
    return None


def premise_of(ev: dict) -> str:
    t = ev.get("evidence_interpretation") or ev.get("evidence_text") or ""
    if ev.get("kind") in ("alert", "news") and ev.get("raw_evidence_text"):
        t = f"{t}\n{ev['raw_evidence_text'][:700]}"
    return t[:1200]


def temporal_relation(ev: dict, claim_time: datetime, t_verify: datetime) -> str:
    pub = _dt(ev.get("published_at"))
    vu = _dt(ev.get("valid_until"))
    if ev.get("superseded_by"):
        return "superseded"
    if vu and vu < t_verify and vu < claim_time:
        return "expired_before_claim"
    if pub is None:
        return "unknown"
    if pub < claim_time - timedelta(hours=6):
        rel = "before"
    elif pub <= claim_time + timedelta(hours=6):
        rel = "contemporary"
    else:
        rel = "after"
    if vu and vu < t_verify:
        rel += "+now_stale"
    return rel


# ---------------- main ----------------

def verify(text: str, posted_at: str | None = None, context: str = "CURRENT", verification_time: str | None = None,
           lat: float | None = None, lon: float | None = None, place: str | None = None, hazard_hint: str | None = None,
           claim_id: str | None = None, channel: str = "tipline", source_metadata: dict | None = None,
           persist: bool = True, live: bool = True, scope: str | None = None) -> dict:
    t0 = time.time()
    trace: list[dict] = []
    t_verify = _dt(verification_time) or datetime.now(timezone.utc)
    claim_time = _dt(posted_at) or t_verify
    context = (context or "CURRENT").upper()

    tt = time.time()
    ex = extract(text, _iso(claim_time))
    trace.append({"step": "extract", "secs": round(time.time() - tt, 1), "method": ex.get("method"), "llm_error": ex.get("llm_error"),
                  "dropped_ungrounded": ex.get("ungrounded_dropped"), "location_span": ex.get("location_span")})
    hazard = hazard_hint or ex.get("hazard") or "unknown"
    props = ex.get("propositions") or []
    for i, p in enumerate(props):
        p["id"] = f"p{i + 1}"
    factual = [p for p in props if p.get("factuality") == "FACTUAL"]
    claim_id = claim_id or new_id("clm_")

    base = {"claim_id": claim_id, "claim_text": text, "verification_context": context, "hazard": hazard,
            "language": ex.get("language"), "claim_time": _iso(claim_time), "verification_time": _iso(t_verify)}
    if not ex.get("is_claim") or not factual:
        res = base | {"checkworthy": False, "status": None,
                      "triage_reason": ex.get("not_claim_reason") or "no checkable factual assertion",
                      "atomic_propositions": [_pub(p) for p in props]}
        trace.append({"step": "triage", "checkworthy": False})
        res["trace"] = trace
        if persist:
            _persist_claim(res, ex, None, channel, posted_at)
        return res

    # --- geography (never invent coordinates) ---
    geo = {"claim_location": ex.get("location_span") or place, "resolved": None, "uncertainty": None}
    if lat is not None and lon is not None:
        geo["resolved"] = {"lat": lat, "lon": lon, "precision": "provided"}
    else:
        q = ex.get("location_query") or place
        g = geo_mod.geocode(q) if q else {"unresolved": True, "reason": "no place mentioned"}
        if g.get("unresolved"):
            geo["uncertainty"] = g["reason"]
        else:
            lat, lon = g["lat"], g["lon"]
            geo["resolved"] = {"lat": lat, "lon": lon, "precision": g["precision"], "display": g.get("display"),
                               "ambiguous": g.get("ambiguous")}
    trace.append({"step": "geocode", **geo})
    ed = _dt((ex.get("event_date") or "")[:10] + "T12:00:00Z") if ex.get("event_date") else None
    event_day = ed if ed and abs((ed - claim_time).days) < 3650 else claim_time
    place_words = []
    for s in (ex.get("location_span"), ex.get("location_query"), place):
        if s:
            place_words += [w.strip(" ,.") for w in s.replace(",", " ").split()]

    pq = [p["text_en"].rstrip(".") for p in factual if p.get("materiality") == "detail" or p.get("type") in ("damage", "casualty", "directive", "infrastructure")]
    cands = gather(hazard, lat, lon, place_words, event_day, t_verify, ex.get("language") or "en",
                   ex.get("location_query") or place, live and scope != "synthetic", trace, pq, scope)
    bound, cands = bind_event(hazard, lat, lon, event_day, cands, trace)

    # --- relevance ranking (embeddings) ---
    tt = time.time()
    if cands and factual:
        P = models.embed([p["text_en"] for p in factual], "query")
        E = models.embed([premise_of(e)[:500] for e in cands], "passage")
        sims = P @ E.T
    else:
        sims = np.zeros((len(factual), len(cands)))

    # --- stance per (fact, evidence) ---
    links = []
    nli_jobs = []
    for i, p in enumerate(factual):
        order = np.argsort(-sims[i]) if len(cands) else []
        picked = 0
        for j in order:
            ev = cands[j]
            r = rule_stance(p, ev, hazard, event_day, claim_time)
            if r is None:
                if picked >= 4 or sims[i][j] < 0.80:
                    continue
                picked += 1
                nli_jobs.append((len(links), premise_of(ev), p["text_en"]))
                r = {"ent": None, "con": None, "rule": None}
            links.append({"p": p, "ev": ev, "sim": float(sims[i][j]), **r})
    if nli_jobs:
        res_nli = models.nli([(a, b) for _, a, b in nli_jobs])
        for (k, _, _), pr in zip(nli_jobs, res_nli):
            news_item = links[k]["ev"].get("kind") == "news"
            # headlines are terse: NLI contradictions on them are noisy, so they count for less
            links[k]["ent"] = pr["entailment"] * (0.85 if news_item else 1.0)
            links[k]["con"] = pr["contradiction"] * (0.5 if news_item else 1.0)
            links[k]["rule"] = f"NLI: entail {pr['entailment']:.2f} / contradict {pr['contradiction']:.2f}"
            links[k]["kind"] = "POSITIVE_CONTRADICTION"

    trace.append({"step": "stance", "pairs_nli": len(nli_jobs), "links": len(links), "secs": round(time.time() - tt, 1)})
    # --- weights, validity per context, independence ---
    t_ctx = claim_time if context == "HISTORICAL" else t_verify
    seen_groups = set()
    for L in sorted(links, key=lambda x: x["ev"].get("published_at") or ""):
        ev = L["ev"]
        w = _trust(ev) * ev["_geo"]
        if ev.get("copy_group_id"):
            key = (L["p"]["id"], ev["copy_group_id"])
            if key in seen_groups:
                w, L["copy"] = 0.0, True
            seen_groups.add(key)
        L["w"] = w
        vu, vf = _dt(ev.get("valid_until")), _dt(ev.get("valid_from"))
        L["valid_at_claim"] = not (vu and vu < claim_time - timedelta(hours=1))
        L["valid_now"] = not (vu and vu < t_ctx) and not ev.get("superseded_by")
        L["relation"] = temporal_relation(ev, claim_time, t_verify)

    # --- proposition states ---
    def noisy_or(items):
        """items: (source_key, value). Max within one source; noisy-OR across independent sources."""
        best: dict = {}
        for k, v in items:
            best[k] = max(best.get(k, 0.0), max(0.0, min(1.0, v)))
        x = 1.0
        for v in best.values():
            x *= (1 - v)
        return 1 - x

    def skey(L):
        ev = L["ev"]
        return ev.get("copy_group_id") or (ev.get("source_id"), ev.get("source_name"))

    p_states = []
    for p in props:
        if p.get("factuality") != "FACTUAL":
            p_states.append(_pub(p) | {"state": p["factuality"], "evidence_ids": []})
            continue
        Ls = [L for L in links if L["p"] is p]
        sup_valid = [(skey(L), L["w"] * L["ent"]) for L in Ls if L["ent"] and L["valid_at_claim"] and (context == "HISTORICAL" or L["valid_now"])]
        sup_stale = [(skey(L), L["w"] * L["ent"]) for L in Ls if L["ent"] and L["valid_at_claim"] and not L["valid_now"]]
        con = [(skey(L), L["w"] * L["con"]) for L in Ls if L["con"] and not L.get("superseding")]
        superseding = [L for L in Ls if L.get("superseding")]
        S, Cn, Sst = noisy_or(sup_valid), noisy_or(con), noisy_or(sup_stale)
        layers = {L["ev"].get("layer") for L in Ls if L["ent"] and L["w"] * L["ent"] > 0.25}
        if len(layers) >= 2:
            S = min(1.0, S * 1.2)
        if Cn >= C.THETA_X and Cn > S:
            st = "CONTRADICTED"
        elif context == "CURRENT" and superseding and (p.get("quantity_type") or p.get("type") in ("casualty", "quantity")):
            st = "SUPERSEDED"
        elif S >= C.THETA_V and Cn < C.THETA_X:
            st = "SUPPORTED"
        elif S >= C.THETA_V and Cn >= C.THETA_X:
            st = "DISPUTED"
        elif context == "CURRENT" and Sst >= C.THETA_V:
            st = "SUPERSEDED"
        elif context == "CURRENT" and superseding:
            st = "SUPERSEDED"
        else:
            st = "UNVERIFIED"
        kinds = [L.get("kind") for L in Ls if L["con"] and L["w"] * L["con"] > 0.2 and L.get("kind")]
        p_states.append(_pub(p) | {"state": st, "support": round(S, 3), "contra": round(Cn, 3),
                                   "support_stale": round(Sst, 3), "layers": sorted(x for x in layers if x),
                                   "contra_kind": kinds[0] if kinds else None,
                                   "superseding": [L["rule"] for L in superseding],
                                   "evidence_ids": sorted({L["ev"]["evidence_id"] for L in Ls if (L["ent"] or 0) + (L["con"] or 0) > 0.2})})

    status, subtype = decide(p_states, context, geo, cands)
    fact_states = [s for s in p_states if s["state"] not in ("SUBJECTIVE", "NON_FACTUAL")]
    mat = [s for s in fact_states] or [{"support": 0, "contra": 0}]
    conf = float(np.mean([abs(s.get("support", 0) - s.get("contra", 0)) / (s.get("support", 0) + s.get("contra", 0) + 0.5) for s in mat]))
    if status == "UNVERIFIED":
        conf = float(np.mean([1 - max(s.get("support", 0), s.get("contra", 0)) for s in mat])) * 0.6

    def ev_card(L):
        ev = L["ev"]
        return {"evidence_id": ev["evidence_id"], "source": ev.get("source_name"), "layer": ev.get("layer"),
                "credibility_tier": ev.get("credibility_tier"), "kind": ev.get("kind"),
                "published_at": ev.get("published_at"), "retrieved_at": ev.get("retrieved_at"),
                "valid_until": ev.get("valid_until"), "location": ev.get("location_text"),
                "lat": ev.get("latitude"), "lon": ev.get("longitude"), "geo_basis": ev.get("_geo_basis"),
                "excerpt": (ev.get("raw_evidence_text") or "")[:400], "interpretation": ev.get("evidence_interpretation"),
                "url": ev.get("source_url"), "temporal_relation": L["relation"], "proposition_id": L["p"]["id"],
                "weight": round(L["w"], 3), "entail": round(L["ent"] or 0, 3), "contradict": round(L["con"] or 0, 3),
                "reason": L.get("rule"), "copy_of_earlier": bool(L.get("copy")),
                "provenance_status": ev.get("provenance_status"), "is_synthetic": bool(ev.get("is_synthetic"))}

    supporting = [ev_card(L) for L in links if (L["ent"] or 0) * L["w"] >= 0.25]
    contradicting = [ev_card(L) for L in links if (L["con"] or 0) * L["w"] >= 0.25 and not L.get("superseding")]
    superseding_cards = [ev_card(L) for L in links if L.get("superseding") or (L["ent"] and not L["valid_now"])]
    uncertainty = []
    if geo.get("uncertainty"):
        uncertainty.append(f"location not resolved: {geo['uncertainty']}")
    if geo.get("resolved", {}) and (geo["resolved"] or {}).get("ambiguous"):
        uncertainty.append("place name is ambiguous (several matches)")
    for s in fact_states:
        if s["state"] == "UNVERIFIED":
            uncertainty.append(f"not confirmed or contradicted by any source: \"{s['text']}\"")
        if s["state"] == "SUPPORTED" and len(s.get("layers", [])) == 1:
            uncertainty.append(f"only one source layer supports: \"{s['text']}\"")
    if any(c["provenance_status"] == "PROVISIONAL" for c in supporting + contradicting):
        uncertainty.append("some evidence has provisional provenance")
    if ex.get("method") != "gemini":
        uncertainty.append("claim extracted with rules only (LLM unavailable)")

    result = base | {
        "checkworthy": True, "status": status, "verification_subtype": subtype, "confidence": round(conf, 3),
        "atomic_propositions": p_states, "supporting_evidence": supporting, "contradicting_evidence": contradicting,
        "superseded_or_stale_evidence": superseding_cards,
        "temporal_analysis": {"claim_time": _iso(claim_time), "event_time": ex.get("event_date"),
                              "verification_time": _iso(t_verify), "context_time": _iso(t_ctx), "bound_event": bound},
        "geographic_analysis": geo, "uncertainty": uncertainty,
        "explanation": explain(status, subtype, p_states, context, supporting, contradicting, superseding_cards),
        "latency_s": round(time.time() - t0, 2),
    }
    trace.append({"step": "decide", "status": status, "subtype": subtype})
    result["trace"] = trace
    if persist:
        _persist_claim(result, ex, (lat, lon), channel, posted_at, links)
    return result


def _pub(p: dict) -> dict:
    return {"id": p.get("id"), "text": p.get("text_en"), "source_span": p.get("source_span"), "type": p.get("type"),
            "materiality": p.get("materiality"), "factuality": p.get("factuality"),
            "quantity": {"type": p.get("quantity_type"), "value": p.get("quantity_value")} if p.get("quantity_type") else None}


def decide(ps: list[dict], context: str, geo: dict, cands: list[dict]) -> tuple[str, str]:
    f = [s for s in ps if s["state"] not in ("SUBJECTIVE", "NON_FACTUAL")]
    st = [s["state"] for s in f]
    if "CONTRADICTED" in st:
        k = next((s["contra_kind"] for s in f if s["state"] == "CONTRADICTED" and s.get("contra_kind")), "POSITIVE_CONTRADICTION")
        return "CONFLICTING", k
    if "DISPUTED" in st:
        return "CONFLICTING", "SOURCE_DISAGREEMENT"
    if context == "CURRENT" and "SUPERSEDED" in st and all(x in ("SUPPORTED", "SUPERSEDED", "UNVERIFIED") for x in st) \
            and any(s["state"] == "SUPERSEDED" and s["materiality"] == "core" or s["state"] == "SUPERSEDED" and s["type"] in ("directive", "casualty", "quantity") for s in f):
        sup = [s for s in f if s["state"] == "SUPERSEDED"]
        if any(s["type"] == "directive" for s in sup):
            return "OUTDATED", "SUPERSEDED_DIRECTIVE"
        if any(s["type"] in ("casualty", "quantity") or s.get("quantity") for s in sup):
            return "OUTDATED", "SUPERSEDED_STATISTIC"
        return "OUTDATED", "SUPERSEDED_SITUATION"
    if st and all(x == "SUPPORTED" for x in st):
        if context == "HISTORICAL" and any(s.get("superseding") for s in f):
            return "VERIFIED", "HISTORICAL_SNAPSHOT"
        layers = set().union(*[set(s.get("layers", [])) for s in f])
        return "VERIFIED", "MULTI_SOURCE_CONFIRMATION" if len(layers) >= 2 else "FACTUAL_CONFIRMATION"
    if any(s["state"] == "SUPPORTED" and s["materiality"] == "core" for s in f):
        return "UNVERIFIED", "PARTIALLY_SUPPORTED"
    if not geo.get("resolved"):
        return "UNVERIFIED", "LOCATION_UNRESOLVED"
    if not cands:
        return "UNVERIFIED", "NO_SOURCE_COVERAGE"
    return "UNVERIFIED", "INSUFFICIENT_EVIDENCE"


def explain(status, subtype, ps, context, sup, con, stale) -> str:
    def cite(cards, pid):
        ids = [c["evidence_id"] for c in cards if c["proposition_id"] == pid][:3]
        return f" [{', '.join(ids)}]" if ids else ""
    lines = []
    for s in ps:
        if s["state"] in ("SUBJECTIVE", "NON_FACTUAL"):
            lines.append(f"• \"{s['text']}\" is {s['state'].lower().replace('_', '-')} and was not used in the decision.")
        elif s["state"] == "SUPPORTED":
            lines.append(f"• Supported: \"{s['text']}\"{cite(sup, s['id'])}.")
        elif s["state"] == "CONTRADICTED":
            lines.append(f"• Contradicted by positive evidence: \"{s['text']}\"{cite(con, s['id'])}.")
        elif s["state"] == "DISPUTED":
            lines.append(f"• Credible sources disagree on: \"{s['text']}\"{cite(sup + con, s['id'])}.")
        elif s["state"] == "SUPERSEDED":
            lines.append(f"• Was supported when posted but is no longer current: \"{s['text']}\"{cite(stale, s['id'])}.")
        else:
            lines.append(f"• No source confirms or contradicts: \"{s['text']}\" (absence of evidence is not treated as false).")
    head = {"VERIFIED": "Verified", "CONFLICTING": "Conflicting", "OUTDATED": "Outdated", "UNVERIFIED": "Unverified"}[status]
    return f"{head} ({subtype.replace('_', ' ').lower()}, {context.lower()} context).\n" + "\n".join(lines)


def _persist_claim(res, ex, latlon, channel, posted_at, links=None):
    c = conn()
    lat, lon = latlon if latlon else (None, None)
    gp = (res.get("geographic_analysis") or {}).get("resolved") or {}
    c.execute("""INSERT OR IGNORE INTO claims (claim_id, claim_text, source_id, source_type, published_at, retrieved_at,
                 event_type, location_text, latitude, longitude, extracted_entities, is_synthetic, channel, language,
                 geo_precision, event_time, bound_event_id, checkworthy, triage_reason)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (res["claim_id"], res["claim_text"], "src_tipline", "social_media", posted_at, now(),
               res.get("hazard") if res.get("hazard") in C.HAZARDS else "unknown", ex.get("location_span"), lat, lon,
               json.dumps({k: ex.get(k) for k in ("location_query", "event_date", "normalized_en", "method")}, ensure_ascii=False),
               0, channel, ex.get("language"), gp.get("precision"), ex.get("event_date"),
               (res.get("temporal_analysis") or {}).get("bound_event"), int(bool(res.get("checkworthy"))),
               res.get("triage_reason")))
    for p in res.get("atomic_propositions", []):
        insert("propositions", {"proposition_id": f"{res['claim_id']}_{p['id']}", "claim_id": res["claim_id"],
                                "idx": int(p["id"][1:]) if p.get("id") else 0, "text": p.get("source_span") or p.get("text"),
                                "text_en": p.get("text"), "type": p.get("type"),
                                "materiality": p.get("materiality") if p.get("materiality") in ("core", "detail") else None,
                                "factuality": p.get("factuality") if p.get("factuality") in ("FACTUAL", "SUBJECTIVE", "NON_FACTUAL") else None,
                                "quantity": p.get("quantity")}, replace=True)
    for L in links or []:
        if (L.get("ent") or 0) + (L.get("con") or 0) < 0.2:
            continue
        rel = "SUPPORTS" if (L["ent"] or 0) >= (L["con"] or 0) else "CONTRADICTS"
        insert("claim_evidence_links", {"link_id": new_id("lnk_"), "claim_id": res["claim_id"],
                                        "evidence_id": L["ev"]["evidence_id"], "relationship": rel,
                                        "support_strength": round(min(1, max(L["ent"] or 0, L["con"] or 0)), 3),
                                        "reason": L.get("rule"), "proposition_id": f"{res['claim_id']}_{L['p']['id']}",
                                        "temporal_relation": L.get("relation"), "p_ent": L.get("ent"), "p_con": L.get("con"),
                                        "weight": L.get("w"), "verification_context": res["verification_context"]})
    if res.get("status"):
        v = rows("SELECT COALESCE(MAX(version),0) AS v FROM verdicts WHERE claim_id=? AND verification_context=?",
                 (res["claim_id"], res["verification_context"]))[0]["v"]
        insert("verdicts", {"verdict_id": new_id("vrd_"), "claim_id": res["claim_id"], "version": v + 1,
                            "verification_context": res["verification_context"], "status": res["status"],
                            "subtype": res.get("verification_subtype"), "confidence": res.get("confidence"),
                            "proposition_states": res.get("atomic_propositions"), "uncertainty": res.get("uncertainty"),
                            "explanation": res.get("explanation"), "result_json": {k: v for k, v in res.items() if k != "trace"},
                            "trace_json": res.get("trace")})
    c.commit()
