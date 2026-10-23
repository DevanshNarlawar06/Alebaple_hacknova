"""
load_sources.py — Seed the sources table from data/source_registry.json.

Run this ONCE after initializing the database.
Idempotent — safe to re-run (uses INSERT OR REPLACE).

Usage:
    python scripts/load_sources.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, get_db, now_utc, PROJECT_ROOT

logger = get_logger("load_sources")

REGISTRY = PROJECT_ROOT / "data" / "source_registry.json"


def main():
    if not REGISTRY.exists():
        logger.error(f"source_registry.json not found at {REGISTRY}")
        sys.exit(1)

    with open(REGISTRY) as f:
        registry = json.load(f)

    conn   = get_db()
    cursor = conn.cursor()
    loaded = 0

    for src in registry.get("sources", []):
        cursor.execute("""
            INSERT OR REPLACE INTO sources (
                source_id, source_name, source_type, source_url,
                authority_level, officiality, timestamp_precision,
                geographic_precision, license, retrieval_method,
                credibility_tier, notes, schema_version
            ) VALUES (
                :source_id, :source_name, :source_type, :source_url,
                :authority_level, :officiality, :timestamp_precision,
                :geographic_precision, :license, :retrieval_method,
                :credibility_tier, :notes, :schema_version
            )
        """, src)
        loaded += 1
        logger.info(f"Loaded source: {src['source_id']} ({src['source_name']})")

    conn.commit()
    conn.close()

    print(f"\nCOMPLETED: {loaded} sources loaded into sources table")
    print(f"\nNEXT: Run scripts/download_gdacs.py and scripts/download_reliefweb.py")


if __name__ == "__main__":
    main()
