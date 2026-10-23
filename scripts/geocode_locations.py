"""
geocode_locations.py — Resolve location_text to lat/lon using Nominatim.

Uses OpenStreetMap Nominatim (free, no API key required).
All results are cached in data/geocode_cache.json to avoid re-querying.

IMPORTANT: Nominatim usage policy requires:
  - 1 request per second maximum
  - A descriptive User-Agent header
  - No bulk commercial usage

This script respects the 1 req/sec limit via sleep(1).

Usage:
    python scripts/geocode_locations.py --table claims
    python scripts/geocode_locations.py --table evidence
    python scripts/geocode_locations.py --table both
    python scripts/geocode_locations.py --dry-run
"""

import argparse
import json
import sys
import time
from pathlib import Path

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, get_db, now_utc, PROJECT_ROOT
import os
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logger = get_logger("geocode_locations")

CACHE_PATH    = PROJECT_ROOT / "data" / "geocode_cache.json"
USER_AGENT    = os.getenv("NOMINATIM_USER_AGENT", "disaster_verification_hacknova26/1.0")
RATE_LIMIT    = 1.1   # seconds between requests (slightly above 1s to be safe)
MAX_RECORDS   = 500   # safety cap per run to avoid abuse


def load_cache() -> dict:
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def geocode_one(geolocator, location_text: str, cache: dict) -> tuple:
    """
    Geocode a single location_text string.
    Returns (latitude, longitude) or (None, None) on failure.
    Uses cache to avoid redundant requests.
    """
    if not location_text or location_text.strip().upper() in ("UNKNOWN", ""):
        return None, None

    key = location_text.strip().lower()
    if key in cache:
        cached = cache[key]
        return cached.get("lat"), cached.get("lon")

    try:
        loc = geolocator.geocode(location_text, timeout=10)
        time.sleep(RATE_LIMIT)  # rate limit — do not remove

        if loc:
            cache[key] = {"lat": loc.latitude, "lon": loc.longitude,
                          "address": loc.address, "queried_at": now_utc()}
            return loc.latitude, loc.longitude
        else:
            cache[key] = {"lat": None, "lon": None, "queried_at": now_utc()}
            logger.debug(f"No geocode result for: {location_text!r}")
            return None, None

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding error for {location_text!r}: {e}")
        return None, None


def update_table(conn, table: str, geolocator, cache: dict, dry_run: bool) -> tuple:
    """
    Find distinct location_text in `table` where latitude IS NULL.
    Geocode each distinct string once, then batch update all matching rows.
    """
    id_col = "claim_id" if table == "claims" else "evidence_id"

    # Find distinct locations needing geocoding
    distinct_locs = conn.execute(f"""
        SELECT DISTINCT location_text
        FROM {table}
        WHERE latitude IS NULL
          AND location_text IS NOT NULL
          AND location_text != ''
          AND location_text != 'UNKNOWN'
    """).fetchall()

    logger.info(f"Table '{table}': {len(distinct_locs)} distinct locations need geocoding")

    resolved_rows = failed_rows = 0
    for (location_text,) in distinct_locs:
        lat, lon = geocode_one(geolocator, location_text, cache)

        count = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE location_text=? AND latitude IS NULL
        """, (location_text,)).fetchone()[0]

        if lat is not None:
            if not dry_run:
                conn.execute(f"""
                    UPDATE {table}
                    SET latitude=?, longitude=?
                    WHERE location_text=? AND latitude IS NULL
                """, (lat, lon, location_text))
            resolved_rows += count
            logger.info(f"Resolved {count} rows for {location_text!r} → ({lat:.4f}, {lon:.4f})")
        else:
            failed_rows += count
            logger.warning(f"Could not resolve {count} rows for {location_text!r}")

    if not dry_run:
        conn.commit()

    return resolved_rows, failed_rows


def main():
    parser = argparse.ArgumentParser(description="Geocode location_text fields in SQLite.")
    parser.add_argument("--table",   choices=["claims", "evidence", "both"], default="both")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cache = load_cache()
    geolocator = Nominatim(user_agent=USER_AGENT)

    conn = get_db()
    tables = ["claims", "evidence"] if args.table == "both" else [args.table]

    total_resolved = total_failed = 0
    for table in tables:
        r, f = update_table(conn, table, geolocator, cache, dry_run=args.dry_run)
        total_resolved += r
        total_failed   += f
        logger.info(f"Table '{table}': resolved={r}, failed={f}")

    conn.close()
    save_cache(cache)

    print(f"\nCOMPLETED")
    print(f"Resolved:  {total_resolved}")
    print(f"Failed:    {total_failed} (set to NULL — may need human review)")
    print(f"Cache:     {CACHE_PATH} ({len(cache)} entries)")
    if args.dry_run:
        print("[DRY RUN — no DB changes written]")
    print(f"\nNEXT: Run scripts/validate_dataset.py to check quality")


if __name__ == "__main__":
    main()
