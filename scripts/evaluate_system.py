"""
evaluate_system.py — Evaluate the verification system against the benchmark.

Reads dataset/benchmark/eval_set.jsonl and sends each claim to the
verification system's API. Compares predicted status to expected_status.

REQUIRES:
  - Benchmark built (run build_benchmark.py first)
  - Application running (FastAPI backend)
  - APPLICATION_URL configured in .env

Produces:
  dataset/reports/evaluation_report.md
  dataset/reports/failure_analysis.md

Usage:
    python scripts/evaluate_system.py --app-url http://localhost:8000
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, now_utc, PROJECT_ROOT

logger = get_logger("evaluate_system")

BENCHMARK_PATH = PROJECT_ROOT / "dataset" / "benchmark" / "eval_set.jsonl"
REPORTS_DIR    = PROJECT_ROOT / "dataset" / "reports"

FAILURE_CATEGORIES = [
    "CLAIM_EXTRACTION_ERROR",
    "SOURCE_RETRIEVAL_ERROR",
    "SOURCE_RANKING_ERROR",
    "FRESHNESS_ERROR",
    "GEOGRAPHIC_ERROR",
    "CONTRADICTION_ERROR",
    "LLM_REASONING_ERROR",
    "HALLUCINATION",
    "INSUFFICIENT_EVIDENCE_HANDLING_ERROR",
]


def main():
    if not BENCHMARK_PATH.exists():
        logger.error(f"Benchmark not found: {BENCHMARK_PATH}")
        logger.error("Run scripts/build_benchmark.py first.")
        sys.exit(1)

    cases = []
    with open(BENCHMARK_PATH) as f:
        for line in f:
            cases.append(json.loads(line.strip()))

    logger.info(f"Loaded {len(cases)} benchmark cases")
    print("STUB: evaluate_system.py requires the application to be running.")
    print(f"Benchmark has {len(cases)} cases ready.")
    print("Implement the evaluation loop once the FastAPI backend is available.")
    print("See dataset/reports/ for output location.")


if __name__ == "__main__":
    main()
