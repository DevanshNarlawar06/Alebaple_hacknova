"""
download_reliefweb.py — Download humanitarian reports from ReliefWeb.

Source: ReliefWeb (managed by UN OCHA)
        https://reliefweb.int
API:    https://apidoc.reliefweb.int
Access: Public REST API — no authentication key required for basic access.
        App name recommended in request headers (configured via .env).

Data role: EVIDENCE (humanitarian situation reports, disaster updates)
           NOT used as claims.

Output:
    dataset/raw/reliefweb/reliefweb_reports_<date>.jsonl

Usage:
    python scripts/download_reliefweb.py [--limit 200] [--disaster-type flood,earthquake]
    python scripts/download_reliefweb.py --country IN --limit 100

NOTE: Rate limit is enforced (1 req/sec). Do not remove the sleep.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, now_utc, PROJECT_ROOT
import os
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logger = get_logger("download_reliefweb")

RELIEFWEB_API  = "https://api.reliefweb.int/v1/reports"
APP_NAME       = os.getenv("RELIEFWEB_APP_NAME", "disaster_verification_hacknova26")
RAW_DIR        = PROJECT_ROOT / "dataset" / "raw" / "reliefweb"
RATE_LIMIT_SEC = 1.0   # 1 request per second — respect ReliefWeb policy

DISASTER_TYPE_MAP = {
    "flood":      "flood",
    "earthquake": "earthquake",
    "cyclone":    "cyclone",
    "wildfire":   "wild fire",
    "drought":    "drought",
    "tsunami":    "tsunami",
    "landslide":  "land slide",
}


def build_query(
    disaster_types: list = None,
    country: str = None,
    days_back: int = 365,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """Build a ReliefWeb API query body."""
    conditions = []

    if disaster_types:
        rw_types = [DISASTER_TYPE_MAP.get(d, d) for d in disaster_types]
        conditions.append({
            "field": "disaster_type.name",
            "value": rw_types,
            "operator": "OR"
        })

    if country:
        conditions.append({
            "field": "country.iso3",
            "value": country.upper()
        })

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00+00:00")
    conditions.append({
        "field": "date.created",
        "value": {"from": from_date}
    })

    query = {
        "query": {"value": "disaster", "operator": "AND"},
        "filter": {"operator": "AND", "conditions": conditions} if conditions else {},
        "fields": {
            "include": [
                "id", "title", "body", "date.created", "date.changed",
                "country.name", "country.iso3",
                "disaster_type.name", "source.name",
                "url", "url_alias", "status"
            ]
        },
        "sort": ["date.created:desc"],
        "limit": limit,
        "offset": offset
    }
    return query


def fetch_page(query: dict) -> dict:
    """Fetch a single page from the ReliefWeb API."""
    headers = {"User-Agent": f"{APP_NAME}/1.0"}
    resp = requests.post(
        RELIEFWEB_API,
        json=query,
        headers=headers,
        params={"appname": APP_NAME},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def normalize_rw_report(report: dict, retrieved_at: str) -> dict:
    """
    Normalize a single ReliefWeb report into canonical evidence schema.
    """
    fields = report.get("fields", {})

    # Extract text — prefer body, fall back to title
    body  = fields.get("body", "") or ""
    title = fields.get("title", "") or ""
    text  = f"{title}. {body[:2000]}".strip() if body else title

    country_data = fields.get("country", [{}])
    country_iso3 = country_data[0].get("iso3", "UNKNOWN") if country_data else "UNKNOWN"
    country_name = country_data[0].get("name", "")         if country_data else ""

    dtype_data = fields.get("disaster_type", [{}])
    dtype_name = dtype_data[0].get("name", "other").lower() if dtype_data else "other"

    # Map ReliefWeb disaster type to canonical event_type
    event_type = "other"
    for canonical, rw_name in DISASTER_TYPE_MAP.items():
        if rw_name in dtype_name:
            event_type = canonical
            break

    pub_date = (fields.get("date", {}) or {}).get("created", "UNKNOWN")
    url = fields.get("url_alias") or fields.get("url") or ""

    return {
        "evidence_id":    None,
        "source_id":      "src_reliefweb",
        "source_name":    "ReliefWeb",
        "source_url":     url,
        "evidence_text":  text[:3000],  # cap at 3000 chars for embedding
        "published_at":   pub_date,
        "retrieved_at":   retrieved_at,
        "event_type":     event_type,
        "location_text":  country_name,
        "latitude":       None,         # ReliefWeb does not provide coordinates
        "longitude":      None,
        "country":        country_iso3, # will be converted ISO3→ISO2 in normalize step
        "region":         "UNKNOWN",
        "credibility_tier": "B",
        "is_synthetic":   0,
        "raw_id":         report.get("id"),
        "schema_version": "0.1"
    }


def download_all(
    disaster_types: list = None,
    country: str = None,
    days_back: int = 365,
    max_records: int = 200
) -> list:
    """Paginate through ReliefWeb API and collect up to max_records reports."""
    records = []
    offset  = 0
    page_size = min(100, max_records)

    while len(records) < max_records:
        query = build_query(
            disaster_types=disaster_types,
            country=country,
            days_back=days_back,
            limit=page_size,
            offset=offset
        )
        logger.info(f"Fetching ReliefWeb page offset={offset} limit={page_size}")

        try:
            data = fetch_page(query)
        except requests.RequestException as e:
            logger.error(f"ReliefWeb request failed at offset={offset}: {e}")
            break

        page_items = data.get("data", [])
        if not page_items:
            logger.info("No more results from ReliefWeb.")
            break

        retrieved_at = now_utc()
        for item in page_items:
            rec = normalize_rw_report(item, retrieved_at)
            if rec["evidence_text"]:
                records.append(rec)

        logger.info(f"Page: {len(page_items)} items | Total so far: {len(records)}")

        total_available = data.get("totalCount", 0)
        if offset + page_size >= total_available:
            break

        offset += page_size
        time.sleep(RATE_LIMIT_SEC)   # rate limit — do not remove

    return records


def main():
    parser = argparse.ArgumentParser(description="Download ReliefWeb humanitarian reports.")
    parser.add_argument("--limit",         type=int,   default=200,
                        help="Maximum number of reports to download (default: 200)")
    parser.add_argument("--disaster-type", type=str,   default="",
                        help="Comma-separated disaster types: flood,earthquake,cyclone,...")
    parser.add_argument("--country",       type=str,   default="",
                        help="Filter by ISO3 country code, e.g. IND, BGD, PHL")
    parser.add_argument("--days-back",     type=int,   default=365,
                        help="How many days of history (default: 365)")
    args = parser.parse_args()

    dtypes  = [d.strip() for d in args.disaster_type.split(",") if d.strip()] or None
    country = args.country.strip().upper() or None

    logger.info(f"Starting ReliefWeb download: max={args.limit} types={dtypes} country={country}")

    records = download_all(
        disaster_types=dtypes,
        country=country,
        days_back=args.days_back,
        max_records=args.limit
    )

    if not records:
        logger.warning("No records downloaded. Check filters or network.")
        sys.exit(0)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    date_str  = now_utc()[:10]
    out_path  = RAW_DIR / f"reliefweb_reports_{date_str}.jsonl"

    with open(out_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    logger.info(f"Saved {len(records)} records to {out_path}")

    print(f"\nCOMPLETED")
    print(f"Output:  {len(records)} ReliefWeb reports")
    print(f"File:    {out_path}")
    print(f"\nNEXT: Run scripts/normalize_evidence.py to load into SQLite")


if __name__ == "__main__":
    main()
