"""
generate_synthetic_cases.py — Generate controlled synthetic test cases.

This script is a STUB. Do NOT run until:
  1. Real evidence data is downloaded and normalized.
  2. Real events suitable for augmentation are selected.
  3. 5 candidate cases are shown to the human and approved.

Workflow:
  Step 1: Identify real events from evidence table (automated)
  Step 2: Generate 5 candidate cases (LLM-assisted)
  Step 3: STOP for human review and approval
  Step 4: After approval, scale to full set

Usage:
    python scripts/generate_synthetic_cases.py --step 1   (identify events)
    python scripts/generate_synthetic_cases.py --step 2   (generate 5 candidates)
    python scripts/generate_synthetic_cases.py --step 4   (scale after approval)

REQUIRES: GEMINI_API_KEY in .env
"""

import sys
print("STUB: generate_synthetic_cases.py is not yet ready to run.")
print("Run after real evidence data is available and approved events are selected.")
print("See workflow state: dataset_workflow_state.json")
sys.exit(0)
