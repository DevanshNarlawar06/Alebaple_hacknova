"""
migrate_v02.py — Additive migration of evidence.db from schema v0.1 to v0.2 (PRD §13).

- Backs up the DB first (data/db/backups/evidence_v01_<ts>.db).
- Only ADDs columns/tables; never drops or rewrites existing columns.
- Data fixes: quarantine wrong geocodes, ISO-8601 GDACS dates, raw_evidence_text + hash,
  provenance_status, source layers.
- Idempotent: safe to run twice.
- Logs to dataset_changelog.md and human_decisions.csv.

Usage: python scripts/migrate_v02.py
"""
import csv
import email.utils
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import PROJECT_ROOT, SQLITE_DB_PATH, get_db, get_logger, now_utc

log = get_logger("migrate_v02")

NEW_COLUMNS = {
    "sources": ["layer TEXT"],
    "claims": [
        "channel TEXT", "language TEXT", "geo_precision TEXT", "geo_confidence REAL",
        "event_time TEXT", "bound_event_id TEXT", "checkworthy INTEGER", "triage_reason TEXT",
        "priority REAL", "story_id TEXT", "media_ids TEXT", "provenance TEXT",
    ],
    "evidence": [
        "raw_evidence_text TEXT", "evidence_interpretation TEXT", "kind TEXT", "layer TEXT",
        "source_document_id TEXT", "retrieval_method TEXT", "evidence_hash TEXT", "license_notes TEXT",
        "provenance_status TEXT", "valid_from TEXT", "valid_until TEXT", "superseded_by TEXT",
        "msg_type TEXT", "severity TEXT", "urgency TEXT", "certainty TEXT", "polygon_geojson TEXT",
        "bbox TEXT", "quantities TEXT", "copy_group_id TEXT", "is_group_origin INTEGER",
        "embedding BLOB", "language TEXT", "event_ref TEXT",
    ],
    "claim_evidence_links": [
        "proposition_id TEXT", "temporal_relation TEXT", "p_ent REAL", "p_con REAL",
        "weight REAL", "excerpt TEXT", "verification_context TEXT",
    ],
    "ground_truth": [
        "verification_context TEXT", "verification_subtype TEXT", "atomic_propositions TEXT",
        "supporting_evidence TEXT", "contradicting_evidence TEXT", "temporal_analysis TEXT",
        "geographic_analysis TEXT", "uncertainty TEXT", "is_synthetic INTEGER", "provenance TEXT",
        "review_decision TEXT",
    ],
}

NEW_TABLES = """
CREATE TABLE IF NOT EXISTS propositions (
    proposition_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, idx INTEGER, text TEXT NOT NULL,
    text_en TEXT, type TEXT, materiality TEXT CHECK(materiality IN ('core','detail')),
    factuality TEXT CHECK(factuality IN ('FACTUAL','SUBJECTIVE','NON_FACTUAL')),
    quantity TEXT, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
CREATE TABLE IF NOT EXISTS ground_truth_cases (
    case_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, verification_context TEXT NOT NULL
        CHECK(verification_context IN ('HISTORICAL','CURRENT')),
    expected_status TEXT NOT NULL CHECK(expected_status IN ('VERIFIED','CONFLICTING','OUTDATED','UNVERIFIED')),
    verification_subtype TEXT, atomic_propositions TEXT, supporting_evidence TEXT,
    contradicting_evidence TEXT, temporal_analysis TEXT, geographic_analysis TEXT, uncertainty TEXT,
    reasoning TEXT, is_synthetic INTEGER NOT NULL DEFAULT 0, provenance TEXT, verification_time TEXT,
    review_decision TEXT CHECK(review_decision IN ('APPROVE','EDIT','REJECT','PENDING')),
    reviewer TEXT, reviewed_at TEXT, split TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(claim_id, verification_context));
CREATE TABLE IF NOT EXISTS stories (
    story_id TEXT PRIMARY KEY, hazard TEXT, rep_claim_id TEXT, place_text TEXT, lat REAL, lon REAL,
    first_seen_at TEXT, last_seen_at TEXT, post_count INTEGER DEFAULT 0, languages TEXT,
    priority REAL, spread_30m INTEGER, current_verdict_id TEXT, embedding BLOB);
CREATE TABLE IF NOT EXISTS verdicts (
    verdict_id TEXT PRIMARY KEY, claim_id TEXT, story_id TEXT, version INTEGER,
    verification_context TEXT, status TEXT, subtype TEXT, confidence REAL, support REAL, contra REAL,
    proposition_states TEXT, uncertainty TEXT, explanation TEXT, result_json TEXT, trace_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY, source_id TEXT, kind TEXT, lat REAL, lon REAL, start_at TEXT, end_at TEXT,
    value REAL, unit TEXT, is_forecast INTEGER, raw_json TEXT, fetched_at TEXT);
CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY, label TEXT, lat REAL, lon REAL, radius_km REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY, subscription_id TEXT, level TEXT, title TEXT, body TEXT, story_id TEXT,
    evidence_id TEXT, created_at TEXT, acked_at TEXT);
CREATE TABLE IF NOT EXISTS media (
    id TEXT PRIMARY KEY, path TEXT, kind TEXT, phash TEXT, dhash TEXT, keyframe_hashes TEXT,
    clip_labels TEXT, first_seen_at TEXT, first_seen_source TEXT);
CREATE TABLE IF NOT EXISTS api_cache (
    url_hash TEXT PRIMARY KEY, url TEXT, fetched_at TEXT, status INTEGER, body BLOB);
CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY, created_at TEXT, split TEXT, metrics TEXT, confusion TEXT, failures TEXT, config TEXT);
CREATE INDEX IF NOT EXISTS idx_ev_layer ON evidence(layer, event_type);
CREATE INDEX IF NOT EXISTS idx_ev_doc ON evidence(source_document_id);
CREATE INDEX IF NOT EXISTS idx_claims_story ON claims(story_id);
CREATE INDEX IF NOT EXISTS idx_props_claim ON propositions(claim_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_claim ON verdicts(claim_id, verification_context, version);
"""

BAD_GEOCODES = {  # location_text -> reason (found in handover inspection)
    "Texas/Louisiana, USA": "Nominatim resolved to 'USA Nails, Bossier City' (a business)",
    "Caribbean/Florida, USA": "Nominatim resolved to Port St. Lucie, FL (not the Caribbean)",
    "Iran/Iraq border region": "cache entry appears hand-typed, not a geocoder result",
}
LAYERS = {"src_gdacs": "official", "src_ndma": "official", "src_reliefweb": "national_global",
          "src_crisismmd": "social"}


def columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def to_iso(s):
    if not s:
        return s
    if len(s) >= 19 and s[4] == "-" and "T" in s:
        return s
    try:
        dt = email.utils.parsedate_to_datetime(s)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return s


def main():
    db = Path(SQLITE_DB_PATH)
    backup_dir = db.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    src = get_db()
    src.execute("PRAGMA wal_checkpoint(FULL)")
    src.close()
    bk = backup_dir / f"evidence_v01_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(db, bk)
    log.info(f"Backup written: {bk}")

    conn = get_db()
    added = 0
    for table, cols in NEW_COLUMNS.items():
        have = columns(conn, table)
        for c in cols:
            name = c.split()[0]
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {c}")
                added += 1
    conn.executescript(NEW_TABLES)
    log.info(f"Columns added: {added}; new tables ensured")

    # --- data fixes ---
    n_geo = 0
    for loc, why in BAD_GEOCODES.items():
        rows = conn.execute("SELECT claim_id, latitude, longitude FROM claims WHERE location_text=? "
                            "AND (geo_precision IS NULL OR geo_precision!='dataset_event_region')", (loc,)).fetchall()
        for r in rows:
            prov = json.dumps({"quarantined_geocode": {"lat": r["latitude"], "lon": r["longitude"], "reason": why}})
            conn.execute("UPDATE claims SET geo_precision='dataset_event_region', geo_confidence=0.2, "
                         "provenance=COALESCE(provenance, ?) WHERE claim_id=?", (prov, r["claim_id"]))
        n_geo += len(rows)
    conn.execute("UPDATE claims SET geo_precision='dataset_event_region', geo_confidence=COALESCE(geo_confidence,0.4) "
                 "WHERE source_id='src_crisismmd' AND geo_precision IS NULL")
    conn.execute("UPDATE claims SET channel='crisismmd' WHERE source_id='src_crisismmd' AND channel IS NULL")

    n_dates = 0
    for r in conn.execute("SELECT evidence_id, published_at FROM evidence").fetchall():
        iso = to_iso(r["published_at"])
        if iso != r["published_at"]:
            conn.execute("UPDATE evidence SET published_at=? WHERE evidence_id=?", (iso, r["evidence_id"]))
            n_dates += 1
    for r in conn.execute("SELECT evidence_id, evidence_text FROM evidence WHERE raw_evidence_text IS NULL").fetchall():
        h = hashlib.sha256(r["evidence_text"].encode("utf-8")).hexdigest()
        conn.execute("UPDATE evidence SET raw_evidence_text=evidence_text, evidence_hash=? WHERE evidence_id=?",
                     (h, r["evidence_id"]))
    conn.execute("UPDATE evidence SET kind='alert', layer='official', retrieval_method='rss', "
                 "provenance_status='VALIDATED' WHERE source_id='src_gdacs' AND kind IS NULL")
    for sid, layer in LAYERS.items():
        conn.execute("UPDATE sources SET layer=? WHERE source_id=? AND layer IS NULL", (layer, sid))
    conn.commit()
    log.info(f"Quarantined geocodes on {n_geo} claims; ISO dates fixed on {n_dates} evidence rows")

    # --- bookkeeping ---
    changelog = PROJECT_ROOT / "dataset_changelog.md"
    if "## v0.2" not in changelog.read_text(encoding="utf-8"):
        with open(changelog, "a", encoding="utf-8") as f:
            f.write(f"""
## v0.2 — {now_utc()[:10]} — Additive migration for the verification engine (PRD §13)

**Changes:** added columns to sources/claims/evidence/claim_evidence_links/ground_truth; new tables
propositions, ground_truth_cases, stories, verdicts, observations, subscriptions, notifications, media,
api_cache, eval_runs. No columns or rows dropped. Backup: `{bk.name}`.

**Data fixes:** {n_geo} CrisisMMD claims with wrong geocodes quarantined
(`geo_precision='dataset_event_region'`, original coords kept in `provenance`); {n_dates} GDACS dates
converted RFC-822 → ISO-8601; `raw_evidence_text` + `evidence_hash` filled; source layers set.

**Deprecated:** `ground_truth.freshness_threshold_hours` (fixed-hours freshness contradicts the
validity-window methodology). Kept, unused.
""")
    dec = PROJECT_ROOT / "human_decisions.csv"
    existing = dec.read_text(encoding="utf-8")
    rows = [
        ("DEC-002", "MERGE_HANDOVER", "PRD v1.2", "Continue handover benchmark vs merge into SachVerify PRD?",
         "A merge / B handover-first / C ignore", "A", "User chose A (merge)"),
        ("DEC-003", "SCHEMA_MIGRATION", "schema v0.2", "Apply additive migration v0.1→v0.2?",
         "Approve / Reject", "Approve", "User instructed to start building; migration is additive with backup"),
        ("DEC-004", "SOURCE_ACCESS", "src_ndma", "NDMA access method (PMA-004)?",
         "A manual / B scraping / C skip / D SACHET CAP feed", "D",
         "SACHET is NDMA's official public CAP feed; no scraping needed"),
        ("DEC-005", "SOURCE_ACCESS", "src_reliefweb", "ReliefWeb live API?",
         "Live / Cached-only", "Cached-only", "Configured appname returns 403 (not approved) on 2026-10-23"),
    ]
    with open(dec, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            if r[0] not in existing:
                w.writerow([r[0], now_utc()[:10], r[1], r[2], r[3], r[4], r[5], r[6], "human" if r[0] in ("DEC-002",) else "agent+user"])
    conn.close()
    print("COMPLETED migrate_v02")


if __name__ == "__main__":
    main()
