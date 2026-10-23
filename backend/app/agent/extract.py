"""Claim extraction + atomic decomposition (PRD §7.3, FR-2).

Primary: Gemini with a strict JSON schema. Grounding guard: every proposition's `source_span` and the
`location_span` must be verbatim substrings of the post, otherwise they are dropped.
Fallback (no LLM): multilingual lexicon + regex; one proposition per sentence.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from ..ml.llm import LLMError, generate_json

HAZARD_ENUM = ["flood", "earthquake", "cyclone", "wildfire", "landslide", "drought", "tsunami", "heatwave",
               "storm", "other", "unknown"]
PTYPES = ["event", "location", "time", "quantity", "casualty", "directive", "damage", "infrastructure", "other"]
QTYPES = ["magnitude", "rainfall_mm", "deaths", "injured", "evacuated", "missing", "affected", "wave_height_m",
          "water_depth_m", "wind_kmh", "temperature_c", "other"]

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_claim": {"type": "BOOLEAN"},
        "not_claim_reason": {"type": "STRING", "nullable": True},
        "language": {"type": "STRING"},
        "hazard": {"type": "STRING", "enum": HAZARD_ENUM},
        "location_span": {"type": "STRING", "nullable": True},
        "location_query": {"type": "STRING", "nullable": True},
        "country_code": {"type": "STRING", "nullable": True},
        "event_date": {"type": "STRING", "nullable": True},
        "normalized_en": {"type": "STRING"},
        "propositions": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "text_en": {"type": "STRING"},
            "source_span": {"type": "STRING"},
            "type": {"type": "STRING", "enum": PTYPES},
            "materiality": {"type": "STRING", "enum": ["core", "detail"]},
            "factuality": {"type": "STRING", "enum": ["FACTUAL", "SUBJECTIVE", "NON_FACTUAL"]},
            "quantity_type": {"type": "STRING", "enum": QTYPES, "nullable": True},
            "quantity_value": {"type": "NUMBER", "nullable": True},
        }, "required": ["text_en", "source_span", "type", "materiality", "factuality"]}},
    },
    "required": ["is_claim", "language", "hazard", "normalized_en", "propositions"],
}

PROMPT = """You extract verifiable factual claims from a disaster-related social media post for a verification system.
Rules:
- Split the post into ATOMIC propositions (one checkable fact each), written in English in `text_en`.
- `source_span` MUST be a contiguous, exact copy of characters from the post (the part stating that fact). Several
  propositions may share the same source_span. Never paraphrase inside source_span.
- materiality: "core" = the disaster event itself happened at that place/time; "detail" = numbers, damage, directives, specifics.
- factuality: SUBJECTIVE for feelings/personal experience/opinions ("scariest quake ever"), NON_FACTUAL for prayers,
  questions, appeals, jokes, URLs; FACTUAL otherwise. Do not invent facts that are not in the post.
- quantity_type/quantity_value only if the proposition states a number (magnitude, deaths, mm of rain, metres...).
- directive = an instruction/order such as evacuation or closure.
- location_span: verbatim place name from the post (or null). location_query: the same place as an English,
  geocodable string with region/country (e.g. "Acapulco, Guerrero, Mexico"). Do not add places not mentioned.
- event_date: ISO date (YYYY-MM-DD) of the event if stated or clearly implied relative to the post time, else null.
- is_claim=false if the post makes no checkable factual assertion about a disaster.
Post time (UTC): {posted_at}
Post:
<<<
{text}
>>>"""

LEX = {
    "flood": ["flood", "flooding", "waterlogging", "water-logging", "waterlogged", "ft of water", "feet of water", "knee-deep", "knee deep", "water entering", "water level", "overflow", "inundat", "dam burst", "dam failure", "बाढ़",
              "पूर", "पाणी", "జలమయం", "వరద", "submerged", "under water", "heavy rain", "बारिश", "पाऊस", "cloudburst"],
    "earthquake": ["earthquake", "quake", "tremor", "भूकंप", "magnitude", "richter", "sismo", "temblor", "భూకంపం"],
    "cyclone": ["cyclone", "hurricane", "typhoon", "चक्रवात", "landfall", "తుఫాను"],
    "tsunami": ["tsunami", "सुनामी"],
    "landslide": ["landslide", "भूस्खलन", "mudslide"],
    "wildfire": ["wildfire", "forest fire", "bushfire", "fire"],
    "heatwave": ["heatwave", "heat wave", "लू"],
    "storm": ["storm", "thunderstorm", "lightning", "बिजली", "పిడుగు"],
}
NON_CLAIM = re.compile(r"\b(pray|praying|stay safe|thoughts with|donate|donation|help needed\?|rip)\b|🙏", re.I)


def lexicon_hazard(text: str) -> str:
    t = text.lower()
    best, n = "unknown", 0
    for hz, words in LEX.items():
        c = sum(w in t for w in words)
        if c > n:
            best, n = hz, c
    return best


def _fallback(text: str) -> dict:
    hz = lexicon_hazard(text)
    sents = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", re.sub(r"https?://\S+", "", text)) if len(s.strip()) > 8]
    props = []
    for i, s in enumerate(sents[:5]):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(mm|m\b|metre|meter|ft|dead|deaths|killed|people|magnitude|M)", s, re.I)
        props.append(dict(text_en=s, source_span=s, type="event" if i == 0 else "other",
                          materiality="core" if i == 0 else "detail",
                          factuality="NON_FACTUAL" if NON_CLAIM.search(s) else "FACTUAL",
                          quantity_type=None, quantity_value=float(m.group(1)) if m else None))
    return dict(is_claim=hz != "unknown" and not (NON_CLAIM.search(text) and len(props) <= 1),
                not_claim_reason=None, language="und", hazard=hz, location_span=None, location_query=None,
                country_code=None, event_date=None, normalized_en=text, propositions=props, method="rules")


def extract(text: str, posted_at: str | None) -> dict:
    try:
        out = generate_json(PROMPT.format(text=text, posted_at=posted_at or "unknown"), SCHEMA)
        out["method"] = "gemini"
    except LLMError as e:
        out = _fallback(text)
        out["llm_error"] = str(e)[:200]
    low = text.lower()
    dropped = []
    good = []
    for p in out.get("propositions", []):
        span = (p.get("source_span") or "").strip()
        if span and (span.lower() in low or fuzz.partial_ratio(span.lower(), low) >= 90):
            good.append(p)
        else:
            dropped.append(p.get("text_en"))
    out["propositions"] = good
    out["ungrounded_dropped"] = dropped
    ls = out.get("location_span")
    if not ls and out.get("location_query"):
        first = out["location_query"].split(",")[0].strip()
        if first and first.lower() in low:
            out["location_span"] = ls = first
    if ls and ls.lower() not in low and fuzz.partial_ratio(ls.lower(), low) < 90:
        out["location_span"] = None
        out["location_query"] = None
        out["location_dropped"] = ls
    if not out.get("location_span"):
        out["location_query"] = None
    if out.get("hazard") in (None, "unknown"):
        out["hazard"] = lexicon_hazard(text)
    return out
