"""Settings: paths, keys (from .env), thresholds and per-hazard parameters (PRD §7)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / os.getenv("SQLITE_DB_PATH", "data/db/evidence.db")
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
GEOCODE_CACHE = ROOT / "data" / "geocode_cache.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
GEMINI_FALLBACK = os.getenv("GEMINI_FALLBACK", "gemini-flash-lite-latest")
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT") or "SachVerify-hacknova26/0.1"

# SNAPSHOT_MODE=1 → connectors read only from api_cache/snapshots (offline demo)
SNAPSHOT_MODE = os.getenv("SNAPSHOT_MODE", "0") == "1"
USE_LLM = os.getenv("USE_LLM", "1") == "1" and bool(GEMINI_API_KEY)
USE_NLI = os.getenv("USE_NLI", "1") == "1"

NLI_MODEL = os.getenv("NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")

# --- decision thresholds (tuned on dev split only) ---
THETA_V = float(os.getenv("THETA_V", 0.55))   # support needed for SUPPORTED
THETA_C = float(os.getenv("THETA_C", 0.30))   # contradiction ceiling for SUPPORTED
THETA_X = float(os.getenv("THETA_X", 0.55))   # contradiction needed for CONTRADICTED

# Layer trust (PRD §7.0)
LAYER_TRUST = {"official": 1.0, "sensor": 0.92, "national_global": 0.75, "local_news": 0.65,
               "humanitarian": 0.8, "social": 0.25, "research": 0.5, "synthetic_official": 0.95}
TIER_TRUST = {"A": 1.0, "B": 0.8, "C": 0.65, "D": 0.25}

# Per-hazard geo decay distance D (km) and retrieval radius R (km)
HAZARD_GEO = {"earthquake": (150, 600), "tsunami": (150, 800), "cyclone": (120, 600),
              "flood": (25, 150), "landslide": (15, 80), "storm": (60, 300), "wildfire": (40, 200),
              "heatwave": (80, 300), "drought": (150, 600), "other": (30, 150), "unknown": (30, 150)}

HAZARDS = list(HAZARD_GEO)
