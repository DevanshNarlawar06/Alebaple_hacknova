# SachVerify — Disaster Information Verification Agent (HACKNOVA'26 PS-2)

## Run it

```bash
# backend (Python 3.12; reuses the system PyTorch)
python -m venv --system-site-packages .venv
.venv/Scripts/python -m pip install sqlmodel transformers sentence-transformers dateparser langdetect feedparser google-genai apscheduler imagehash python-dotenv geopy pyyaml rapidfuzz httpx shapely sse-starlette fastapi uvicorn
.venv/Scripts/python scripts/migrate_v02.py          # additive schema v0.1 → v0.2 (backs up the DB first)
.venv/Scripts/python scripts/build_pilots.py         # 5 pilot cases on primary evidence (PENDING review)
.venv/Scripts/python -m uvicorn backend.app.main:app --port 8000

# frontend
cd frontend && npm install && npm run dev            # http://localhost:5173  (/ console · /beacon phone app · /eval)
```

- `.env` needs `GEMINI_API_KEY` (claim extraction). Without it the agent falls back to rules-only extraction.
- In the Console, **Replay demo** streams the synthetic Pune flood + Delhi quake scenarios (all synthetic items are labelled).
- `SNAPSHOT_MODE=1` makes every connector read only from the local cache (offline demo).
- Evaluation: `.venv/Scripts/python scripts/run_eval.py` (approved cases only) or `--include-pending` (dev run, labelled as such).
- Design docs: `docs/PRD.md`, `docs/architecture.svg`, `docs/HANDOVER_STATE.md`, UI designs in `design/`.

---

# Disaster Information Verification System
**HACKNOVA'26 — Problem Statement 2**

A disaster-information verification agent that analyzes disaster-related claims
and compares them against trusted emergency alerts, geographic information,
weather data, timestamps, and other available reports.

---

## Verification Statuses

| Status | Meaning |
|---|---|
| `VERIFIED` | Reliable evidence supports the claim |
| `CONFLICTING` | Evidence contains materially inconsistent information |
| `OUTDATED` | Claim may have been accurate but is no longer current |
| `UNVERIFIED` | Insufficient reliable evidence to establish the claim |

---

## Project Structure

```
Disaster_Info_Verification_System/
├── dataset/            # Dataset pipeline (this team's responsibility)
│   ├── raw/            # Downloaded raw data (gitignored)
│   ├── processed/      # Normalized claims + evidence JSONL
│   ├── synthetic/      # Human-approved synthetic cases
│   ├── ground_truth/   # Human-validated labels
│   ├── benchmark/      # eval_set.jsonl (100 cases)
│   └── reports/        # Quality, evaluation, failure reports
├── data/
│   ├── db/evidence.db  # Canonical SQLite store (shared with app)
│   ├── db/chroma/      # ChromaDB vector store (shared with app)
│   └── source_registry.json
├── schema/schema.sql   # Authoritative SQLite DDL
├── scripts/            # Dataset pipeline scripts
├── tests/              # Automated tests
├── .env.example        # API key template
├── requirements.txt
├── human_decisions.csv
├── dataset_workflow_state.json
└── dataset_changelog.md
```

---

## Quick Start — Dataset Pipeline

```bash
# 1. Set up environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env — add GEMINI_API_KEY at minimum

# 3. Initialize database
sqlite3 data/db/evidence.db < schema/schema.sql

# 4. Load source registry
python scripts/load_sources.py

# 5. Download evidence (automated)
python scripts/download_gdacs.py --days 90
python scripts/download_reliefweb.py --limit 200

# 6. Normalize into SQLite
python scripts/normalize_evidence.py

# 7. Geocode locations
python scripts/geocode_locations.py

# 8. Validate data quality
python scripts/validate_dataset.py

# 9. [MANUAL] Download CrisisMMD — see dataset/raw/crisismmd/README.txt
# python scripts/normalize_claims.py  (after manual download)

# 10. [HUMAN REVIEW] Synthetic cases and ground truth labeling
#     See dataset_workflow_state.json for current stage
```

---

## Data Sources

| Source | Role | Credibility | Access |
|---|---|---|---|
| GDACS | Evidence — official disaster events | Tier A | Public GeoJSON/RSS |
| ReliefWeb | Evidence — humanitarian reports | Tier B | Public REST API |
| CrisisMMD | Claims — social-media posts | Tier D | Manual download (terms required) |
| NDMA India | Evidence — official Indian alerts | Tier A | Pending access decision |

---

## Interface Contract (Dataset → Application)

The dataset pipeline produces; the application consumes:

| File | Description |
|---|---|
| `data/db/evidence.db` | SQLite with sources, claims, evidence, links, ground_truth tables |
| `data/db/chroma/` | ChromaDB vector store (run `scripts/embed_evidence.py` to populate) |
| `data/source_registry.json` | Source credibility metadata |
| `dataset/benchmark/eval_set.jsonl` | 100-case evaluation benchmark |

Schema definition: `schema/schema.sql` — **do not modify without updating dataset_changelog.md**

---

## Schema Version

Current: `v0.1`  
See: `dataset_changelog.md`

---

## Human Decision Log

All material human decisions are recorded in `human_decisions.csv`.

---

## Workflow State

Current pipeline state: `dataset_workflow_state.json`
