"""
normalize_claims.py — Normalize raw claims from CrisisMMD into SQLite.

IMPORTANT: CrisisMMD data must be manually downloaded first.
See dataset/raw/crisismmd/README.txt for download instructions.

CrisisMMD provides TSV files with columns:
  tweet_id, image_id, tweet_text, image, label, label_text, ...

Data role: CLAIMS only. CrisisMMD labels are NOT used as verification
           ground truth. They are used for claim extraction only.

Usage:
    python scripts/normalize_claims.py --input dataset/raw/crisismmd/

Output:
    Rows inserted into claims table in data/db/evidence.db
    dataset/processed/claims.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, get_db, new_id, now_utc, PROJECT_ROOT, SCHEMA_VERSION

logger = get_logger("normalize_claims")

PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"

# CrisisMMD event-to-canonical event_type mapping
CRISISMMD_EVENT_MAP = {
    "hurricane_harvey":         "cyclone",
    "hurricane_irma":           "cyclone",
    "hurricane_maria":          "cyclone",
    "california_wildfires":     "wildfire",
    "greece_wildfires":         "wildfire",
    "saddleridge_wildfire":     "wildfire",
    "mexico_earthquake":        "earthquake",
    "nepal_earthquake2015":     "earthquake",
    "pakistan_earthquake":      "earthquake",
    "iraq_iran_earthquake":     "earthquake",
    "sri_lanka_floods":         "flood",
    "srilanka_floods":          "flood",
    "flood":                    "flood",
    "tsunami":                  "tsunami",
}

# CrisisMMD location hints per event
CRISISMMD_LOCATION_MAP = {
    "hurricane_harvey":         ("Texas/Louisiana, USA", "US"),
    "hurricane_irma":           ("Caribbean/Florida, USA", "US"),
    "hurricane_maria":          ("Puerto Rico, USA", "US"),
    "california_wildfires":     ("California, USA", "US"),
    "greece_wildfires":         ("Greece", "GR"),
    "saddleridge_wildfire":     ("California, USA", "US"),
    "mexico_earthquake":        ("Mexico City, Mexico", "MX"),
    "nepal_earthquake2015":     ("Nepal", "NP"),
    "pakistan_earthquake":      ("Pakistan", "PK"),
    "iraq_iran_earthquake":     ("Iran/Iraq border region", "IR"),
    "sri_lanka_floods":         ("Sri Lanka", "LK"),
    "srilanka_floods":          ("Sri Lanka", "LK"),
}


def find_crisismmd_files(input_dir: Path) -> list:
    """Find all TSV/CSV claim files in the CrisisMMD directory."""
    files = []
    for ext in ["*.tsv", "*.csv"]:
        for p in input_dir.glob(f"**/{ext}"):
            if not p.name.lower().startswith("readme") and not p.name.startswith("._"):
                files.append(p)
    return sorted(files)


def parse_crisismmd_row(row: dict, default_event_name: str, retrieved_at: str) -> dict | None:
    """Parse a single CrisisMMD row into canonical claims schema."""
    text = (row.get("tweet_text") or row.get("text") or "").strip()
    if not text or len(text) < 10:
        return None

    # Check row-level event_name column first, fallback to filename
    row_event = (row.get("event_name") or default_event_name or "").lower()

    event_type = "unknown"
    location_text = "UNKNOWN"
    country = "UNKNOWN"
    for key, canonical in CRISISMMD_EVENT_MAP.items():
        if key in row_event:
            event_type = canonical
            loc_info = CRISISMMD_LOCATION_MAP.get(key, ("UNKNOWN", "UNKNOWN"))
            location_text, country = loc_info
            break

    published_at = "UNKNOWN"

    return {
        "claim_id":              new_id("clm_"),
        "claim_text":            text[:1000],
        "source_id":             "src_crisismmd",
        "source_type":           "social_media",
        "published_at":          published_at,
        "retrieved_at":          retrieved_at,
        "event_type":            event_type,
        "location_text":         location_text,
        "latitude":              None,
        "longitude":             None,
        "country":               country,
        "region":                "UNKNOWN",
        "extracted_entities":    json.dumps({}),
        "is_synthetic":          0,
        "derived_from_event_id": None,
        "generation_method":     None,
        "human_validated":       0,
        "schema_version":        SCHEMA_VERSION,
    }


def load_crisismmd(input_dir: Path) -> list:
    """Load all CrisisMMD files from input_dir with deduplication."""
    files = find_crisismmd_files(input_dir)
    if not files:
        logger.error(f"No TSV/CSV files found in {input_dir}")
        logger.error("Download CrisisMMD from https://crisisnlp.qcri.org/crisismmd and place in dataset/raw/crisismmd/")
        return []

    records = []
    seen_texts = set()
    retrieved_at = now_utc()

    for f in files:
        event_name = f.stem
        logger.info(f"Processing {f.name} (event: {event_name})")

        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                sample = fh.read(4096)
                fh.seek(0)
                delimiter = "\t" if "\t" in sample else ","
                reader = csv.DictReader(fh, delimiter=delimiter)
                for row in reader:
                    text_val = (row.get("tweet_text") or row.get("text") or "").strip()
                    if not text_val or text_val in seen_texts:
                        continue
                    seen_texts.add(text_val)

                    rec = parse_crisismmd_row(row, event_name, retrieved_at)
                    if rec:
                        records.append(rec)
        except Exception as e:
            logger.error(f"Failed to parse {f}: {e}")

    logger.info(f"Loaded {len(records)} unique claims from {len(files)} CrisisMMD files")
    return records


def insert_claims(conn, records: list, dry_run: bool = False) -> tuple:
    inserted = skipped = errors = 0
    cursor = conn.cursor()

    for rec in records:
        if not rec.get("claim_text", "").strip():
            errors += 1
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would insert claim: {rec['claim_id']} | {rec['event_type']} | {rec['country']}")
            inserted += 1
            continue

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO claims (
                    claim_id, claim_text, source_id, source_type,
                    published_at, retrieved_at, event_type,
                    location_text, latitude, longitude, country, region,
                    extracted_entities, is_synthetic, derived_from_event_id,
                    generation_method, human_validated, schema_version
                ) VALUES (
                    :claim_id, :claim_text, :source_id, :source_type,
                    :published_at, :retrieved_at, :event_type,
                    :location_text, :latitude, :longitude, :country, :region,
                    :extracted_entities, :is_synthetic, :derived_from_event_id,
                    :generation_method, :human_validated, :schema_version
                )
            """, rec)
            inserted += 1 if cursor.rowcount > 0 else 0
            skipped  += 1 if cursor.rowcount == 0 else 0
        except Exception as e:
            logger.error(f"DB insert failed: {e}")
            errors += 1

    if not dry_run:
        conn.commit()
    return inserted, skipped, errors


def main():
    parser = argparse.ArgumentParser(description="Normalize CrisisMMD claims into SQLite.")
    parser.add_argument("--input",   type=Path,
                        default=PROJECT_ROOT / "dataset" / "raw" / "crisismmd",
                        help="Path to CrisisMMD raw directory")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        logger.error("CrisisMMD must be manually downloaded. See MANUAL INTERVENTION REQUIRED.")
        sys.exit(1)

    records = load_crisismmd(args.input)
    if not records:
        sys.exit(1)

    conn = get_db()
    inserted, skipped, errors = insert_claims(conn, records, dry_run=args.dry_run)
    conn.close()

    if not args.dry_run and inserted > 0:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        conn2 = get_db()
        rows = conn2.execute("SELECT * FROM claims WHERE is_synthetic=0").fetchall()
        conn2.close()
        out = PROCESSED_DIR / "claims.jsonl"
        with open(out, "w") as f:
            for row in rows:
                f.write(json.dumps(dict(row)) + "\n")
        logger.info(f"Exported {len(rows)} claims to {out}")

    print(f"\nCOMPLETED")
    print(f"Inserted: {inserted} | Skipped: {skipped} | Errors: {errors}")
    if args.dry_run:
        print("[DRY RUN]")
    print(f"\nNEXT: Run scripts/geocode_locations.py")


if __name__ == "__main__":
    main()
