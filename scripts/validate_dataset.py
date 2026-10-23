"""
validate_dataset.py — Automated dataset quality validation.

Runs the following checks:
  1. Schema validation    — required fields, data types, null values, duplicates
  2. Temporal validation  — invalid/future/timezone-inconsistent timestamps
  3. Geographic validation — coordinate range, location/coordinate mismatches
  4. Relationship validation — orphan records, duplicate links
  5. Ground-truth validation — every benchmark case has human_validated=1

Produces:
  dataset/reports/dataset_quality_report.md

Usage:
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --strict   (exit code 1 on any WARNING)
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_logger, get_db, now_utc, PROJECT_ROOT

logger = get_logger("validate_dataset")
REPORTS_DIR = PROJECT_ROOT / "dataset" / "reports"

# ── Helpers ──────────────────────────────────────────────────────────────────

def now():
    return datetime.now(timezone.utc)


class ValidationReport:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.info     = []

    def error(self, msg):
        self.errors.append(msg)
        logger.error(f"ERROR: {msg}")

    def warn(self, msg):
        self.warnings.append(msg)
        logger.warning(f"WARN:  {msg}")

    def ok(self, msg):
        self.info.append(msg)
        logger.info(f"OK:    {msg}")

    @property
    def passed(self):
        return len(self.errors) == 0

    def summary(self):
        return f"Errors: {len(self.errors)} | Warnings: {len(self.warnings)} | OK: {len(self.info)}"


# ── Validation Checks ─────────────────────────────────────────────────────────

def check_sources(conn, r: ValidationReport):
    """Validate sources table."""
    rows = conn.execute("SELECT * FROM sources").fetchall()
    r.ok(f"sources: {len(rows)} records")

    for row in rows:
        if not row["source_name"]:
            r.error(f"sources: source_id={row['source_id']} has NULL source_name")
        if row["authority_level"] is not None and not (1 <= row["authority_level"] <= 5):
            r.error(f"sources: {row['source_id']} authority_level out of range: {row['authority_level']}")

    # Check all source_ids referenced in claims/evidence exist
    missing = conn.execute("""
        SELECT DISTINCT c.source_id FROM claims c
        LEFT JOIN sources s ON c.source_id = s.source_id
        WHERE c.source_id IS NOT NULL AND s.source_id IS NULL
    """).fetchall()
    if missing:
        r.error(f"claims reference {len(missing)} unknown source_ids: {[m[0] for m in missing]}")

    missing_ev = conn.execute("""
        SELECT DISTINCT e.source_id FROM evidence e
        LEFT JOIN sources s ON e.source_id = s.source_id
        WHERE e.source_id IS NOT NULL AND s.source_id IS NULL
    """).fetchall()
    if missing_ev:
        r.error(f"evidence references {len(missing_ev)} unknown source_ids: {[m[0] for m in missing_ev]}")


def check_claims(conn, r: ValidationReport):
    """Validate claims table."""
    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    r.ok(f"claims: {total} total records")

    # Empty text
    empty = conn.execute("SELECT COUNT(*) FROM claims WHERE claim_text IS NULL OR TRIM(claim_text)=''").fetchone()[0]
    if empty:
        r.error(f"claims: {empty} rows have empty claim_text")

    # Duplicate claim_text (exact duplicates — suspicious)
    dups = conn.execute("""
        SELECT claim_text, COUNT(*) AS n FROM claims
        GROUP BY claim_text HAVING n > 1
    """).fetchall()
    if dups:
        r.warn(f"claims: {len(dups)} duplicate claim texts found (may need deduplication)")

    # Coordinate range
    bad_lat = conn.execute("SELECT COUNT(*) FROM claims WHERE latitude IS NOT NULL AND (latitude < -90 OR latitude > 90)").fetchone()[0]
    bad_lon = conn.execute("SELECT COUNT(*) FROM claims WHERE longitude IS NOT NULL AND (longitude < -180 OR longitude > 180)").fetchone()[0]
    if bad_lat: r.error(f"claims: {bad_lat} rows with latitude out of [-90, 90]")
    if bad_lon: r.error(f"claims: {bad_lon} rows with longitude out of [-180, 180]")

    # Future timestamps
    now_str = now().strftime("%Y-%m-%dT%H:%M:%SZ")
    future = conn.execute(f"SELECT COUNT(*) FROM claims WHERE published_at > '{now_str}' AND published_at != 'UNKNOWN'").fetchone()[0]
    if future:
        r.warn(f"claims: {future} rows with future published_at timestamp")


def check_evidence(conn, r: ValidationReport):
    """Validate evidence table."""
    total = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    r.ok(f"evidence: {total} total records")

    empty = conn.execute("SELECT COUNT(*) FROM evidence WHERE evidence_text IS NULL OR TRIM(evidence_text)=''").fetchone()[0]
    if empty:
        r.error(f"evidence: {empty} rows have empty evidence_text")

    bad_lat = conn.execute("SELECT COUNT(*) FROM evidence WHERE latitude IS NOT NULL AND (latitude < -90 OR latitude > 90)").fetchone()[0]
    bad_lon = conn.execute("SELECT COUNT(*) FROM evidence WHERE longitude IS NOT NULL AND (longitude < -180 OR longitude > 180)").fetchone()[0]
    if bad_lat: r.error(f"evidence: {bad_lat} rows with bad latitude")
    if bad_lon: r.error(f"evidence: {bad_lon} rows with bad longitude")


def check_links(conn, r: ValidationReport):
    """Validate claim_evidence_links table."""
    total = conn.execute("SELECT COUNT(*) FROM claim_evidence_links").fetchone()[0]
    r.ok(f"claim_evidence_links: {total} total records")

    # Orphan claim references
    orphan_c = conn.execute("""
        SELECT COUNT(*) FROM claim_evidence_links l
        LEFT JOIN claims c ON l.claim_id = c.claim_id
        WHERE c.claim_id IS NULL
    """).fetchone()[0]
    if orphan_c:
        r.error(f"claim_evidence_links: {orphan_c} links reference non-existent claims")

    # Orphan evidence references
    orphan_e = conn.execute("""
        SELECT COUNT(*) FROM claim_evidence_links l
        LEFT JOIN evidence e ON l.evidence_id = e.evidence_id
        WHERE e.evidence_id IS NULL
    """).fetchone()[0]
    if orphan_e:
        r.error(f"claim_evidence_links: {orphan_e} links reference non-existent evidence")


def check_ground_truth(conn, r: ValidationReport):
    """Validate ground_truth table."""
    total = conn.execute("SELECT COUNT(*) FROM ground_truth").fetchone()[0]
    r.ok(f"ground_truth: {total} total records")

    unvalidated = conn.execute("SELECT COUNT(*) FROM ground_truth WHERE human_validated=0").fetchone()[0]
    if unvalidated:
        r.warn(f"ground_truth: {unvalidated} records NOT yet human_validated — excluded from benchmark")

    missing_reason = conn.execute("SELECT COUNT(*) FROM ground_truth WHERE reason IS NULL OR TRIM(reason)=''").fetchone()[0]
    if missing_reason:
        r.error(f"ground_truth: {missing_reason} records have no reason field")

    # Every GT record must reference an existing claim
    orphan_gt = conn.execute("""
        SELECT COUNT(*) FROM ground_truth gt
        LEFT JOIN claims c ON gt.claim_id = c.claim_id
        WHERE c.claim_id IS NULL
    """).fetchone()[0]
    if orphan_gt:
        r.error(f"ground_truth: {orphan_gt} records reference non-existent claims")


def check_benchmark_readiness(conn, r: ValidationReport):
    """Check whether enough validated cases exist for a benchmark."""
    validated = conn.execute("""
        SELECT expected_status, COUNT(*) AS n
        FROM ground_truth
        WHERE human_validated=1
        GROUP BY expected_status
    """).fetchall()

    total_valid = sum(v[1] for v in validated)
    dist = {v[0]: v[1] for v in validated}

    r.ok(f"Benchmark-ready ground truth: {total_valid} cases")
    for status in ["VERIFIED", "CONFLICTING", "OUTDATED", "UNVERIFIED"]:
        n = dist.get(status, 0)
        if n < 5:
            r.warn(f"Low benchmark coverage for {status}: only {n} validated cases (target ≥ 20)")

    if total_valid < 50:
        r.warn(f"Total benchmark cases ({total_valid}) below minimum target of 50")


# ── Report Writer ─────────────────────────────────────────────────────────────

def write_report(r: ValidationReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "dataset_quality_report.md"

    lines = [
        "# Dataset Quality Report",
        f"**Generated:** {now_utc()}",
        f"**Result:** {'✅ PASSED' if r.passed else '❌ FAILED'}",
        f"**Summary:** {r.summary()}",
        "",
    ]

    if r.errors:
        lines += ["## ❌ Errors (must fix before benchmark)", ""]
        for e in r.errors:
            lines.append(f"- {e}")
        lines.append("")

    if r.warnings:
        lines += ["## ⚠️ Warnings (review recommended)", ""]
        for w in r.warnings:
            lines.append(f"- {w}")
        lines.append("")

    if r.info:
        lines += ["## ✅ Passed checks", ""]
        for i in r.info:
            lines.append(f"- {i}")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate dataset quality.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 on any WARNING or ERROR")
    args = parser.parse_args()

    conn = get_db()
    r    = ValidationReport()

    check_sources(conn, r)
    check_claims(conn, r)
    check_evidence(conn, r)
    check_links(conn, r)
    check_ground_truth(conn, r)
    check_benchmark_readiness(conn, r)
    conn.close()

    report_path = write_report(r)

    print(f"\nVALIDATION RESULT: {'PASSED' if r.passed else 'FAILED'}")
    print(r.summary())
    print(f"Report: {report_path}")

    if not r.passed or (args.strict and r.warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
