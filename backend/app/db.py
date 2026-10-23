"""SQLite access (handover schema v0.2). Thin helpers, no ORM magic."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .config import DB_PATH

_local = threading.local()


def conn() -> sqlite3.Connection:
    c = getattr(_local, "c", None)
    if c is None:
        c = sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        _local.c = c
    return c


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def stable_id(prefix: str, *parts) -> str:
    return prefix + hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def rows(sql: str, params=()) -> list[dict]:
    return [dict(r) for r in conn().execute(sql, params).fetchall()]


def one(sql: str, params=()) -> dict | None:
    r = conn().execute(sql, params).fetchone()
    return dict(r) if r else None


EVIDENCE_COLS = None


def upsert_evidence(ev: dict) -> str:
    """Insert or update an evidence row keyed by evidence_id. Raw text is never overwritten."""
    global EVIDENCE_COLS
    c = conn()
    if EVIDENCE_COLS is None:
        EVIDENCE_COLS = {r[1] for r in c.execute("PRAGMA table_info(evidence)")}
    ev = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
          for k, v in ev.items() if k in EVIDENCE_COLS}
    ev.setdefault("retrieved_at", now())
    ev.setdefault("evidence_text", ev.get("raw_evidence_text") or "")
    if ev.get("raw_evidence_text") and not ev.get("evidence_hash"):
        ev["evidence_hash"] = hashlib.sha256(ev["raw_evidence_text"].encode("utf-8")).hexdigest()
    existing = c.execute("SELECT raw_evidence_text FROM evidence WHERE evidence_id=?", (ev["evidence_id"],)).fetchone()
    if existing:
        ev.pop("raw_evidence_text", None) if existing[0] else None
        sets = ", ".join(f"{k}=?" for k in ev if k != "evidence_id")
        c.execute(f"UPDATE evidence SET {sets} WHERE evidence_id=?",
                  [v for k, v in ev.items() if k != "evidence_id"] + [ev["evidence_id"]])
    else:
        cols = ", ".join(ev)
        c.execute(f"INSERT INTO evidence ({cols}) VALUES ({', '.join('?' * len(ev))})", list(ev.values()))
    c.commit()
    return ev["evidence_id"]


def insert(table: str, row: dict, replace: bool = False):
    row = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in row.items()}
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    conn().execute(f"{verb} INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                   list(row.values()))
    conn().commit()
