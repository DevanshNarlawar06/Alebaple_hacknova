# Dataset Changelog

All significant dataset changes must be recorded here.
Format: `## vX.Y — YYYY-MM-DD — Brief title`

---

## v0.1 — 2026-10-23 — Infrastructure initialized

**Stage:** Infrastructure

**Changes:**
- Created full directory structure
- Created `schema/schema.sql` — canonical SQLite schema (5 tables: sources, claims, evidence, claim_evidence_links, ground_truth)
- Initialized `data/db/evidence.db` from schema
- Created `.env.example`, `.gitignore`
- Created `dataset_workflow_state.json`, `human_decisions.csv`
- Created `requirements.txt`

**Records added:** 0  
**Records removed:** 0  
**Labels changed:** 0  
**Manual decisions:** 0  
**Source changes:** None — no sources configured yet

**Human approvals recorded:**
- Architecture proposal approved by user (2026-10-23)
- Schema v0.1 approved by user (2026-10-23)

**Pending:**
- CrisisMMD download (manual, terms required)
- GDACS download (automated, terms confirmation required)
- ReliefWeb download (automated, terms confirmation required)
- NDMA evaluation (access method TBD)
- Gemini API key (required for synthetic generation)

## v0.2 — 2026-10-23 — Additive migration for the verification engine (PRD §13)

**Changes:** added columns to sources/claims/evidence/claim_evidence_links/ground_truth; new tables
propositions, ground_truth_cases, stories, verdicts, observations, subscriptions, notifications, media,
api_cache, eval_runs. No columns or rows dropped. Backup: `evidence_v01_20261023_162845.db`.

**Data fixes:** 8509 CrisisMMD claims with wrong geocodes quarantined
(`geo_precision='dataset_event_region'`, original coords kept in `provenance`); 294 GDACS dates
converted RFC-822 → ISO-8601; `raw_evidence_text` + `evidence_hash` filled; source layers set.

**Deprecated:** `ground_truth.freshness_threshold_hours` (fixed-hours freshness contradicts the
validity-window methodology). Kept, unused.
