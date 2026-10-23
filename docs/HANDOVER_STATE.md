# Handover State Report — `Disaster_Information_Verification_System.zip`
**Inspected:** 23 Oct 2026 · read-only, extracted to a scratch folder · nothing modified · **Decision taken: Option A (merge into the SachVerify PRD)**

## 1. Repository
- Git repo on `master` with 2 commits:
  - `845cf84` init dataset pipeline (schema v0.1)
  - `cfd9e20` ingest 16k CrisisMMD claims + 294 GDACS alerts
  - `dataset/processed/` and `docs/` are untracked.
- 2,517 of the 2,742 files are a **Python 3.9 virtual environment from macOS/Linux** (`.venv/bin/...`). It can't be used on this Windows machine and will not be copied.
- The git folder has broken leftover references from Codex checkpoints (harmless).
- `.env`:
  - `GEMINI_API_KEY` **set**, `RELIEFWEB_APP_NAME` **set**, `NOMINATIM_USER_AGENT` set, `GDACS_API_KEY` empty.
  - The Gemini key and ReliefWeb name have not been tested yet; testing needs your OK.
  - `.env` is correctly gitignored.

## 2. Database `data/db/evidence.db` (SQLite WAL, schema v0.1)
| Table | Rows | Notes |
|---|---|---|
| sources | 4 | GDACS (A), ReliefWeb (B), CrisisMMD (D), NDMA (A) |
| claims | 16,058 | All CrisisMMD tweets, 2017; 0 synthetic; 0 human-validated |
| evidence | 294 | All live GDACS RSS items (Sep–Oct 2026); 263 are wildfires; 0 in India |
| claim_evidence_links | **0** | |
| ground_truth | **0** | |

## 3. Dataset files
- `dataset/raw/crisismmd/`: the official CrisisMMD v2 split files (text + image-path TSVs; **images not included**).
- `dataset/raw/gdacs/gdacs_events_2026-10-23.jsonl` (snapshot).
- `dataset/processed/claims.jsonl` (10.5 MB) and `evidence.jsonl`.
- `dataset/synthetic/`, `ground_truth/`, `benchmark/` and `raw/reliefweb/` are **empty**. **There is no `eval_set.jsonl`.**

## 4. Scripts
| Script | State |
|---|---|
| `load_sources.py`, `download_gdacs.py`, `normalize_claims.py`, `normalize_evidence.py`, `geocode_locations.py`, `validate_dataset.py`, `utils.py` | Working, and have been run |
| `download_reliefweb.py` | Written; never run (no data in `raw/reliefweb/`) |
| `generate_synthetic_cases.py` | **Stub** (exits immediately) |
| `build_benchmark.py` | Works once ≥ 10 validated ground-truth rows exist |
| `evaluate_system.py` | Shell (expects an app API that doesn't exist yet) |
| `embed_evidence.py` | Referenced in the README; **missing** |

## 5. Application components
**None.** No backend, no UI, no verification logic. The `tests/*` folders are empty.

## 6. Completed vs claimed
| Handover prompt says | Repository shows |
|---|---|
| "Evidence validation COMPLETED, ~12 carefully selected records" | **Not in the repo.** No Guajataca, Tubbs, Atlas, USACE, PTWC or Iran-casualty evidence rows or files. The only matches are ordinary CrisisMMD tweets. |
| "Five pilot cases formally designed (`clm_pilot_001..005`)" | **Not in the repo.** No `clm_pilot_*` anywhere. |
| "Corrections made (rejected tide-gauge record, separated CAL FIRE records, Guajataca timeline, Iran provisional)" | Not visible in any file; they existed only in the previous conversation. |
| Ingestion / links / ground truth / eval not done | ✅ Matches |

## 7. Inconsistencies and data-quality problems
1. **Claims and evidence cannot meet.** Claims are 2017 US/Mexico/Sri Lanka/Iran events; evidence is 2026 GDACS (0 rows before 2020). As loaded, every claim would be UNVERIFIED for lack of evidence, not because of what the evidence says.
2. **Bad geocodes written to about 8,000 claims:**
   - "Texas/Louisiana, USA" → *USA Nails, Bossier City* (3,992 claims)
   - "Caribbean/Florida, USA" → Port St. Lucie (4,021 claims)
   - "Iran/Iraq border region" has a hand-typed address, not a query result.
3. **Location is per dataset event, not per tweet:** all tweets of an event share one coordinate. They should be marked low precision, never shown as exact pins.
4. `dataset_workflow_state.json` is stale (stage INFRASTRUCTURE_COMPLETE, 0 records).
5. `ground_truth.freshness_threshold_hours` is a fixed-hours cutoff, which **contradicts the handover's own rule** (freshness must come from how long information stays valid and from what supersedes it).
6. The schema has nowhere to store: atomic propositions, `verification_context`, `verification_subtype`, `raw_evidence_text` vs interpretation, `provenance_status`, `evidence_hash`, validity windows, or superseded-by links.
7. The GDACS published-date range is stored as RFC-822 strings, so text sorting gives a wrong min/max. Dates need converting to ISO-8601.
8. A handful of tweet texts contain mojibake (`�`).
9. The README says "100-case benchmark"; the handover says "~50". We adopt **~50**.

## 8. Checks I ran on pilot-case evidence (live, 23 Oct 2026)
| Pilot | Primary evidence | Retrievable? | Note |
|---|---|---|---|
| 001 Puebla, VERIFIED | USGS `us2000ar20`: M7.1, 19 Sep 2017, 18.55 N −98.49 W, depth 48 km | ✅ USGS FDSN API | |
| 002 "12 m tsunami at Acapulco", CONFLICTING | Same USGS record: **inland epicentre, 236 km from Acapulco**, `tsunami=0` | ✅ | ⚠️ `tsunami=0` is a *metadata flag*, not a tide-gauge observation; the inland epicentre is the stronger physical argument. ⚠️ The **8 Sep M8.2 Tehuantepec quake (`us2000ahv0`) did produce a tsunami** (`tsunami=1`). The system must tie the claim to the right event by date, or it will wrongly mark this VERIFIED. That makes it a strong test case. |
| 003 Guajataca evacuation, OUTDATED (current) | NWS San Juan "FLASH FLOOD EMERGENCY for Isabela and Quebradillas… Dam Failure", 23 Sep 2017, 7:58 AM and 1:58 PM AST | ✅ Iowa Environmental Mesonet AFOS archive (`FFWSJU`) | The record that supersedes it (USACE work) still needs retrieving |
| 004 Harvey crime rumour, UNVERIFIED | Flood evidence (NWS/USGS) | Not checked yet | The crime claim must stay UNVERIFIED, not CONFLICTING |
| 005 Iran-Iraq casualties, VERIFIED (historical) / OUTDATED (current) | USGS `us2000bmcg`: M7.3, 12 Nov 2017 (event facts only) | ✅ for the event; casualty figures **provisional** | Keep `provenance_status = PROVISIONAL` |

## 9. What we keep (Option A)
- **Methodology rules:**
  - absence ≠ contradiction;
  - HISTORICAL vs CURRENT context;
  - superseding events, not fixed time cutoffs;
  - atomic propositions;
  - excluding subjective content;
  - human review gate;
  - no fabricated evidence.
- **Schema v0.1 tables** as the base, extended to v0.2 (see PRD §13).
- **Their data:** the source registry and credibility tiers, the GDACS downloader, the CrisisMMD claims (as a realistic claim pool, with corrected geo-precision), the validator, and the benchmark builder.
- **Their evaluation design:** per-status metrics + failure categories + critical-error monitoring (UNVERIFIED→CONFLICTING, OUTDATED→CONFLICTING).

## 10. First recommended next step (after PRD review)
Copy the handover repo **without `.venv`** into this workspace as the base. Migrate the schema v0.1 → v0.2 additively; no existing rows dropped, and each change logged in `dataset_changelog.md` and `human_decisions.csv`. Quarantine the bad geocodes. Then rebuild the 5 pilot cases from the retrieved primary records above and send them through the review gate.
