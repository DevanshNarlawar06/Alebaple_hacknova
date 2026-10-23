"""
download_gdacs.py — Download disaster event data from GDACS.

Source: Global Disaster Alert and Coordination System (GDACS)
        https://www.gdacs.org
Access: Public GeoJSON / RSS / ATOM feeds — no authentication required
        for public-tier data. Authenticated API gives more fields.

Data role: EVIDENCE (authoritative disaster event records)
           NOT used as claims.

Output:
    dataset/raw/gdacs/gdacs_events_<date>.json
    dataset/raw/gdacs/gdacs_events_<date>.jsonl  (one event per line)

Usage:
    python scripts/download_gdacs.py [--days 30] [--alert-level orange,red]

NOTE: Run validate_dataset.py after this script to check data quality.
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, now_utc, PROJECT_ROOT

logger = get_logger("download_gdacs")

# GDACS public GeoJSON endpoint
# Returns events from the last N days — no authentication required.
GDACS_GEOJSON_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
GDACS_FEED_URL    = "https://www.gdacs.org/xml/rss.xml"   # fallback RSS

RAW_DIR = PROJECT_ROOT / "dataset" / "raw" / "gdacs"

ALERT_LEVELS = {
    "green":  1,
    "orange": 2,
    "red":    3
}

EVENT_TYPE_MAP = {
    "FL":  "flood",
    "EQ":  "earthquake",
    "TC":  "cyclone",
    "VO":  "volcanic_activity",
    "DR":  "drought",
    "WF":  "wildfire",
    "TS":  "tsunami",
}


def fetch_gdacs_rss(alert_levels: list = None) -> list:
    """
    Fetch GDACS real-time disaster alerts via GeoRSS feed.
    Returns list of normalized evidence records.
    """
    import feedparser

    logger.info(f"Fetching GDACS RSS feed: {GDACS_FEED_URL}")
    feed = feedparser.parse(GDACS_FEED_URL)
    retrieved_at = now_utc()

    if not feed.entries:
        logger.warning("No entries found in GDACS RSS feed.")
        return []

    records = []
    for entry in feed.entries:
        alert_level = getattr(entry, "gdacs_alertlevel", "green").lower()
        if alert_levels and alert_level not in alert_levels:
            continue

        raw_event_type = getattr(entry, "gdacs_eventtype", "").upper()
        event_type = EVENT_TYPE_MAP.get(raw_event_type, "other")

        # Extract coordinates
        lat = getattr(entry, "geo_lat", None)
        lon = getattr(entry, "geo_long", None)
        try:
            latitude = float(lat) if lat is not None else None
            longitude = float(lon) if lon is not None else None
        except (ValueError, TypeError):
            latitude = longitude = None

        from_date = getattr(entry, "gdacs_fromdate", None) or getattr(entry, "published", None) or "UNKNOWN"
        country_name = getattr(entry, "gdacs_country", "") or getattr(entry, "title", "")
        iso3 = getattr(entry, "gdacs_iso3", "UNKNOWN")

        # Build comprehensive narrative text
        desc_parts = [entry.title]
        if getattr(entry, "description", None):
            desc_parts.append(entry.description)
        severity = getattr(entry, "gdacs_severity", None)
        if severity:
            desc_parts.append(f"Severity: {severity}")
        pop = getattr(entry, "gdacs_population", None)
        if pop:
            desc_parts.append(f"Affected Population: {pop}")

        evidence_text = " — ".join(p.strip() for p in desc_parts if p.strip())

        rec = {
            "evidence_id":      None,
            "source_id":        "src_gdacs",
            "source_name":      "GDACS",
            "source_url":       getattr(entry, "link", ""),
            "evidence_text":    evidence_text[:4000],
            "published_at":     from_date,
            "retrieved_at":     retrieved_at,
            "event_type":       event_type,
            "location_text":    country_name,
            "latitude":         latitude,
            "longitude":        longitude,
            "country":          iso3,
            "region":           "UNKNOWN",
            "credibility_tier": "A",
            "is_synthetic":     0,
            "raw":              {k: str(v) for k, v in entry.items() if "gdacs" in k or "geo" in k or k in ("title", "link", "published")},
            "schema_version":   "0.1"
        }
        records.append(rec)

    logger.info(f"Parsed {len(records)} disaster events from GDACS RSS feed")
    return records

def save_raw(records: list, retrieved_at: str) -> Path:
    """Save normalized JSONL to dataset/raw/gdacs/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    date_str = retrieved_at[:10]
    jsonl_path = RAW_DIR / f"gdacs_events_{date_str}.jsonl"

    with open(jsonl_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    logger.info(f"Normalized JSONL saved: {jsonl_path} ({len(records)} records)")

    return jsonl_path


def main():
    parser = argparse.ArgumentParser(description="Download GDACS disaster events.")
    parser.add_argument("--alert-level", type=str, default="green,orange,red",
                        help="Comma-separated alert levels to include")
    args = parser.parse_args()

    alert_levels = [a.strip().lower() for a in args.alert_level.split(",")]
    retrieved_at = now_utc()

    logger.info(f"Starting GDACS download from live feed, levels={alert_levels}")
    records = fetch_gdacs_rss(alert_levels=alert_levels)

    if not records:
        logger.warning("No records returned from GDACS feed.")
        sys.exit(0)

    out_path = save_raw(records, retrieved_at)

    print(f"\nCOMPLETED")
    print(f"Output:   {len(records)} normalized evidence records")
    print(f"File:     {out_path}")
    print(f"\nNEXT: Run scripts/normalize_evidence.py to load into SQLite")


if __name__ == "__main__":
    main()
