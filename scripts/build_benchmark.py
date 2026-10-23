"""
build_benchmark.py — Build the evaluation benchmark from validated ground truth.

Reads ground_truth WHERE human_validated=1 and exports to:
    dataset/benchmark/eval_set.jsonl

IMPORTANT: Only runs when sufficient human-validated cases exist.
           Will refuse to run if validation is incomplete.

Usage:
    python scripts/build_benchmark.py [--min-cases 50]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, get_db, now_utc, PROJECT_ROOT

logger = get_logger("build_benchmark")
BENCHMARK_DIR = PROJECT_ROOT / "dataset" / "benchmark"


def main():
    conn = get_db()

    # Only include human-validated cases
    rows = conn.execute("""
        SELECT gt.*, c.claim_text, c.event_type, c.location_text,
               c.latitude, c.longitude, c.country, c.published_at,
               c.is_synthetic, c.source_id
        FROM ground_truth gt
        JOIN claims c ON gt.claim_id = c.claim_id
        WHERE gt.human_validated = 1
        ORDER BY gt.expected_status, gt.difficulty
    """).fetchall()

    conn.close()

    if len(rows) < 10:
        logger.error(f"Only {len(rows)} validated ground truth cases — minimum 10 required.")
        logger.error("Complete human validation before building benchmark.")
        sys.exit(1)

    # Distribution check
    dist = {}
    for row in rows:
        s = row["expected_status"]
        dist[s] = dist.get(s, 0) + 1
    logger.info(f"Distribution: {dist}")

    for status in ["VERIFIED", "CONFLICTING", "OUTDATED", "UNVERIFIED"]:
        if dist.get(status, 0) == 0:
            logger.warning(f"No cases for status: {status} — benchmark will be incomplete")

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BENCHMARK_DIR / "eval_set.jsonl"

    with open(out_path, "w") as f:
        for row in rows:
            record = dict(row)
            record["benchmark_generated_at"] = now_utc()
            f.write(json.dumps(record) + "\n")

    print(f"\nCOMPLETED")
    print(f"Benchmark cases: {len(rows)}")
    print(f"Distribution:    {dist}")
    print(f"Output:          {out_path}")
    print(f"\nNEXT: Run scripts/evaluate_system.py against the application")


if __name__ == "__main__":
    main()
