"""
normalize_evidence.py — Load and normalize raw evidence into SQLite.

Reads all .jsonl files from dataset/raw/gdacs/ and dataset/raw/reliefweb/,
deduplicates, assigns canonical evidence_ids, resolves ISO country codes,
and inserts into the evidence table in data/db/evidence.db.

Usage:
    python scripts/normalize_evidence.py [--source gdacs] [--source reliefweb]
    python scripts/normalize_evidence.py --dry-run

Output:
    Rows inserted into evidence table in data/db/evidence.db
    dataset/processed/evidence.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, get_db, new_id, now_utc, PROJECT_ROOT, SCHEMA_VERSION

logger = get_logger("normalize_evidence")

RAW_DIR       = PROJECT_ROOT / "dataset" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"

# ISO 3166-1 alpha-3 → alpha-2 mapping (subset relevant to major disaster-prone countries)
ISO3_TO_ISO2 = {
    "IND": "IN", "BGD": "BD", "PHL": "PH", "IDN": "ID", "NPL": "NP",
    "PAK": "PK", "LKA": "LK", "MMR": "MM", "THA": "TH", "VNM": "VN",
    "CHN": "CN", "JPN": "JP", "HTI": "HT", "MEX": "MX", "BRA": "BR",
    "USA": "US", "AUS": "AU", "ETH": "ET", "MOZ": "MZ", "MDG": "MG",
    "NGA": "NG", "KEN": "KE", "TZA": "TZ", "UGA": "UG", "SOM": "SO",
    "SYR": "SY", "YEM": "YE", "AFG": "AF", "IRN": "IR", "IRQ": "IQ",
    "TUR": "TR", "GRC": "GR", "ITA": "IT", "ESP": "ES", "PRT": "PT",
    "UNKNOWN": "UNKNOWN",
}


def load_jsonl(path: Path) -> list:
    records = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"{path}:{i} JSON parse error: {e}")
    return records


def resolve_country(raw: str) -> str:
    """Convert ISO3 to ISO2; if already 2-char, return as-is."""
    if not raw or raw == "UNKNOWN":
        return "UNKNOWN"
    raw = raw.strip().upper()
    if len(raw) == 2:
        return raw
    return ISO3_TO_ISO2.get(raw, raw[:2] if len(raw) >= 2 else "UNKNOWN")


def validate_record(rec: dict) -> list:
    """Return list of validation error strings. Empty list = valid."""
    errors = []
    if not rec.get("evidence_text", "").strip():
        errors.append("evidence_text is empty")
    lat = rec.get("latitude")
    lon = rec.get("longitude")
    if lat is not None:
        try:
            if not (-90 <= float(lat) <= 90):
                errors.append(f"latitude out of range: {lat}")
        except (TypeError, ValueError):
            errors.append(f"latitude not numeric: {lat}")
    if lon is not None:
        try:
            if not (-180 <= float(lon) <= 180):
                errors.append(f"longitude out of range: {lon}")
        except (TypeError, ValueError):
            errors.append(f"longitude not numeric: {lon}")
    return errors


def normalize_record(rec: dict) -> dict:
    """Apply normalizations to a raw record before DB insertion."""
    rec["country"]    = resolve_country(rec.get("country", "UNKNOWN"))
    rec["is_synthetic"] = int(bool(rec.get("is_synthetic", 0)))

    # Truncate text to DB-safe length
    if rec.get("evidence_text"):
        rec["evidence_text"] = rec["evidence_text"][:4000]

    # Strip any raw dump fields not in schema
    for field in ["raw", "raw_id"]:
        rec.pop(field, None)

    return rec


def insert_evidence(conn, records: list, dry_run: bool = False) -> tuple:
    """Insert records into the evidence table. Returns (inserted, skipped, errors)."""
    inserted = skipped = errors = 0
    cursor = conn.cursor()

    for rec in records:
        # Assign a new ID
        rec["evidence_id"] = new_id("ev_")
        rec["retrieved_at"] = rec.get("retrieved_at") or now_utc()
        rec["schema_version"] = SCHEMA_VERSION

        errs = validate_record(rec)
        if errs:
            logger.warning(f"Validation failed for record from {rec.get('source_id')}: {errs}")
            errors += 1
            continue

        rec = normalize_record(rec)

        if dry_run:
            logger.info(f"[DRY RUN] Would insert: {rec['evidence_id']} | {rec['source_id']} | {rec['event_type']} | {rec['country']}")
            inserted += 1
            continue

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO evidence (
                    evidence_id, source_id, source_name, source_url,
                    evidence_text, published_at, retrieved_at,
                    event_type, location_text, latitude, longitude,
                    country, region, credibility_tier, is_synthetic, schema_version
                ) VALUES (
                    :evidence_id, :source_id, :source_name, :source_url,
                    :evidence_text, :published_at, :retrieved_at,
                    :event_type, :location_text, :latitude, :longitude,
                    :country, :region, :credibility_tier, :is_synthetic, :schema_version
                )
            """, rec)
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"DB insert failed: {e} | record: {rec.get('evidence_id')}")
            errors += 1

    if not dry_run:
        conn.commit()

    return inserted, skipped, errors


def main():
    parser = argparse.ArgumentParser(description="Normalize raw evidence into SQLite.")
    parser.add_argument("--source",   type=str, action="append",
                        choices=["gdacs", "reliefweb", "ndma"],
                        help="Source(s) to process. Repeat for multiple. Default: all.")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Validate and print without writing to DB.")
    args = parser.parse_args()

    sources = args.source or ["gdacs", "reliefweb"]

    all_records = []
    for src in sources:
        src_dir = RAW_DIR / src
        if not src_dir.exists():
            logger.warning(f"Raw directory not found: {src_dir} — skipping")
            continue
        jsonl_files = list(src_dir.glob("*.jsonl"))
        if not jsonl_files:
            logger.warning(f"No .jsonl files in {src_dir} — run download_{src}.py first")
            continue
        for f in jsonl_files:
            recs = load_jsonl(f)
            logger.info(f"Loaded {len(recs)} records from {f.name}")
            all_records.extend(recs)

    if not all_records:
        logger.warning("No records to normalize. Download raw data first.")
        sys.exit(0)

    logger.info(f"Total records to normalize: {len(all_records)}")

    conn = get_db()
    inserted, skipped, errors = insert_evidence(conn, all_records, dry_run=args.dry_run)
    conn.close()

    # Export processed JSONL
    if not args.dry_run and inserted > 0:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_path = PROCESSED_DIR / "evidence.jsonl"
        conn2 = get_db()
        rows = conn2.execute("SELECT * FROM evidence").fetchall()
        conn2.close()
        with open(out_path, "w") as f:
            for row in rows:
                f.write(json.dumps(dict(row)) + "\n")
        logger.info(f"Exported {len(rows)} evidence records to {out_path}")

    print(f"\nCOMPLETED")
    print(f"Inserted: {inserted}")
    print(f"Skipped (duplicate): {skipped}")
    print(f"Errors:   {errors}")
    if args.dry_run:
        print("[DRY RUN — no DB changes written]")
    print(f"\nNEXT: Run scripts/geocode_locations.py to resolve coordinates")


if __name__ == "__main__":
    main()
