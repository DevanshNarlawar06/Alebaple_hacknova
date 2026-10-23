"""SachVerify API (FastAPI). Run: .venv/Scripts/python -m uvicorn backend.app.main:app --port 8000"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import config as C
from .agent.verify import verify
from .connectors import gdacs, ndma_cap
from .connectors.base import FetchError
from .connectors.sources import ensure_sources
from .db import insert, new_id, now, one, rows
from .events import bus
from .beacon import threat_for


async def _poller():
    while True:
        for name, fn in (("ndma", lambda: ndma_cap.poll(40)), ("gdacs", gdacs.poll)):
            try:
                got = await asyncio.to_thread(fn)
                bus.publish("alerts.refreshed", {"source": name, "n": len(got)})
            except (FetchError, Exception) as e:  # keep polling on any failure
                bus.publish("connector.error", {"source": name, "error": str(e)[:200]})
        await asyncio.sleep(180)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_sources()
    from .ml import models
    asyncio.get_running_loop().run_in_executor(None, models.warmup)
    task = None if C.SNAPSHOT_MODE else asyncio.create_task(_poller())
    yield
    if task:
        task.cancel()


app = FastAPI(title="SachVerify API", version="0.2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class CheckIn(BaseModel):
    text: str
    posted_at: str | None = None
    verification_context: Literal["CURRENT", "HISTORICAL"] = "CURRENT"
    verification_time: str | None = None
    lat: float | None = None
    lon: float | None = None
    place: str | None = None
    hazard_hint: str | None = None
    source_metadata: dict | None = None
    claim_id: str | None = None


def _run(body: CheckIn, persist: bool, channel: str):
    if len(body.text) > 4000:
        raise HTTPException(413, "text too long (max 4000 chars)")
    res = verify(body.text, body.posted_at, body.verification_context, body.verification_time, body.lat, body.lon,
                 body.place, body.hazard_hint, body.claim_id, channel, body.source_metadata, persist=persist)
    if persist and res.get("status"):
        bus.publish("claim.verdict", {k: res.get(k) for k in ("claim_id", "claim_text", "status", "verification_subtype",
                                                              "confidence", "verification_context")} |
                    {"geo": (res.get("geographic_analysis") or {}).get("resolved")})
    return res


@app.post("/api/claims/check")
async def check(body: CheckIn, include_trace: bool = False):
    res = await asyncio.to_thread(_run, body, False, "check")
    if not include_trace:
        res.pop("trace", None)
    return res


@app.post("/api/tipline")
async def tipline(body: CheckIn):
    res = await asyncio.to_thread(_run, body, True, "tipline")
    res.pop("trace", None)
    return res


@app.get("/api/claims")
def list_claims(status: str | None = None, context: str = "CURRENT", limit: int = 50, channel: str | None = None):
    sql = """SELECT c.claim_id, c.claim_text, c.channel, c.published_at, c.event_type, c.location_text, c.latitude,
                    c.longitude, c.language, v.status, v.subtype, v.confidence, v.verification_context, v.created_at
             FROM verdicts v JOIN claims c ON c.claim_id=v.claim_id
             WHERE v.version=(SELECT MAX(version) FROM verdicts v2 WHERE v2.claim_id=v.claim_id
                              AND v2.verification_context=v.verification_context) AND v.verification_context=?"""
    params: list = [context]
    if status:
        sql += " AND v.status=?"
        params.append(status.upper())
    if channel:
        sql += " AND c.channel=?"
        params.append(channel)
    sql += " ORDER BY v.created_at DESC LIMIT ?"
    params.append(limit)
    return rows(sql, params)


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: str):
    c = one("SELECT * FROM claims WHERE claim_id=?", (claim_id,))
    if not c:
        raise HTTPException(404, "claim not found")
    vs = rows("SELECT verdict_id, version, verification_context, status, subtype, confidence, created_at, result_json "
              "FROM verdicts WHERE claim_id=? ORDER BY verification_context, version", (claim_id,))
    latest = {}
    for v in vs:
        latest[v["verification_context"]] = json.loads(v["result_json"]) if v["result_json"] else None
    history = [{k: v[k] for k in ("version", "verification_context", "status", "subtype", "confidence", "created_at")} for v in vs]
    return {"claim": c, "latest": latest, "history": history}


@app.get("/api/alerts")
def alerts(active: bool = True, source: str | None = None, limit: int = 200):
    sql = ("SELECT evidence_id, source_id, source_name, event_type, severity, urgency, certainty, msg_type, "
           "raw_evidence_text, published_at, valid_from, valid_until, location_text, latitude, longitude, "
           "polygon_geojson, source_url, is_synthetic FROM evidence WHERE kind='alert'")
    p: list = []
    if active:
        sql += " AND (valid_until IS NULL OR valid_until >= ?)"
        p.append(now())
    if source:
        sql += " AND source_id=?"
        p.append(source)
    sql += " ORDER BY published_at DESC LIMIT ?"
    p.append(limit)
    out = rows(sql, p)
    for a in out:
        a["polygon_geojson"] = json.loads(a["polygon_geojson"]) if a["polygon_geojson"] else None
    return out


@app.get("/api/map")
def map_features(context: str = "CURRENT", limit: int = 300):
    feats = []
    for a in alerts(active=True, limit=limit):
        if a["polygon_geojson"]:
            feats.append({"type": "Feature", "geometry": a["polygon_geojson"],
                          "properties": {"layer": "alert_area", **{k: a[k] for k in ("evidence_id", "source_name", "event_type", "severity", "valid_until")}}})
        if a["latitude"] is not None:
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [a["longitude"], a["latitude"]]},
                          "properties": {"layer": "alert", **{k: a[k] for k in ("evidence_id", "source_name", "event_type", "severity", "valid_until")}}})
    for c in list_claims(context=context, limit=limit):
        if c["latitude"] is not None:
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [c["longitude"], c["latitude"]]},
                          "properties": {"layer": "claim", **{k: c[k] for k in ("claim_id", "claim_text", "status", "subtype", "confidence")}}})
    return {"type": "FeatureCollection", "features": feats}


class SubIn(BaseModel):
    lat: float
    lon: float
    radius_km: float = 10
    label: str | None = None


@app.post("/api/beacon/subscribe")
def subscribe(b: SubIn):
    sid = new_id("sub_")
    insert("subscriptions", {"id": sid, "label": b.label, "lat": round(b.lat, 2), "lon": round(b.lon, 2),
                             "radius_km": b.radius_km, "created_at": now()})
    return {"subscription_id": sid}


@app.get("/api/beacon/{sub_id}/status")
def beacon_status(sub_id: str):
    s = one("SELECT * FROM subscriptions WHERE id=?", (sub_id,))
    if not s:
        raise HTTPException(404, "subscription not found")
    return threat_for(s["lat"], s["lon"], s["radius_km"])


@app.get("/api/beacon/status")
def beacon_status_at(lat: float = Query(...), lon: float = Query(...), radius_km: float = 10):
    return threat_for(round(lat, 2), round(lon, 2), radius_km)


@app.get("/api/eval/latest")
def eval_latest():
    r = one("SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT 1")
    if not r:
        return {"available": False}
    return {k: (json.loads(v) if k in ("metrics", "confusion", "failures", "config") and v else v) for k, v in r.items()}


@app.get("/api/stream")
async def stream():
    q = bus.subscribe()

    async def gen():
        try:
            while True:
                ev = await q.get()
                yield {"event": ev["type"], "data": json.dumps(ev["data"], ensure_ascii=False, default=str)}
        finally:
            bus.unsubscribe(q)
    return EventSourceResponse(gen(), ping=15)


class ReplayIn(BaseModel):
    scenarios: list[str] | None = None
    seconds_per_minute: float = 1.5


@app.post("/api/admin/replay")
async def replay(b: ReplayIn):
    from . import scenarios as S
    posts = await asyncio.to_thread(S.build, b.scenarios)
    bus.publish("replay.started", {"scenarios": b.scenarios or list(S.SCENARIOS), "posts": len(posts)})

    async def run():
        last = 0
        for p in posts:
            await asyncio.sleep(max(0.0, (p["offset_min"] - last) * b.seconds_per_minute))
            last = p["offset_min"]
            bus.publish("post.received", {"text": p["text"], "scenario": p["scenario"], "synthetic": True})
            try:
                res = await asyncio.to_thread(lambda: verify(p["text"], p["posted_at"], "CURRENT", None, p["lat"], p["lon"],
                                                             channel="replay", scope="synthetic"))
                if res.get("status"):
                    bus.publish("claim.verdict", {k: res.get(k) for k in ("claim_id", "claim_text", "status",
                                                                          "verification_subtype", "confidence")} |
                                {"geo": (res.get("geographic_analysis") or {}).get("resolved"),
                                 "scenario": p["scenario"], "demo_expected": p["expected"], "synthetic": True})
                else:
                    bus.publish("post.filtered", {"text": p["text"], "reason": res.get("triage_reason")})
            except Exception as e:
                bus.publish("verify.error", {"text": p["text"], "error": str(e)[:200]})
        bus.publish("replay.finished", {})
    asyncio.create_task(run())
    return {"started": True, "posts": [{k: p[k] for k in ("offset_min", "text", "scenario")} for p in posts]}


@app.post("/api/admin/ingest-now")
async def ingest_now():
    out = {}
    for name, fn in (("ndma", lambda: ndma_cap.poll(40)), ("gdacs", gdacs.poll)):
        try:
            out[name] = len(await asyncio.to_thread(fn))
        except Exception as e:
            out[name] = f"error: {str(e)[:150]}"
    return out


@app.get("/api/health")
def health():
    counts = {t: one(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in ("evidence", "claims", "verdicts", "ground_truth_cases")}
    return {"ok": True, "snapshot_mode": C.SNAPSHOT_MODE, "llm": C.USE_LLM, "llm_model": C.GEMINI_MODEL,
            "nli_model": C.NLI_MODEL, "embed_model": C.EMBED_MODEL, "counts": counts}
