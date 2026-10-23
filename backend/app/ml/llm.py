"""Gemini (REST) with JSON output, deterministic settings and a response cache.

The LLM is used only for claim extraction / atomic decomposition. Every string it returns that must come
from the post is checked to be a verbatim substring (grounding guard); otherwise it is dropped.
"""
from __future__ import annotations

import hashlib
import json

import httpx

from ..config import GEMINI_API_KEY, GEMINI_FALLBACK, GEMINI_MODEL, USE_LLM
from ..db import conn, now

URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


class LLMError(Exception):
    pass


def generate_json(prompt: str, schema: dict, *, timeout: float = 45) -> dict:
    last = None
    for m in (GEMINI_MODEL, GEMINI_MODEL, GEMINI_FALLBACK):  # one retry, then the lighter model
        try:
            return _generate(prompt, schema, m, timeout)
        except LLMError as e:
            last = e
    raise last


def _generate(prompt: str, schema: dict, model: str, timeout: float) -> dict:
    if not USE_LLM:
        raise LLMError("LLM disabled")
    key = hashlib.sha1((model + json.dumps(schema, sort_keys=True) + prompt).encode()).hexdigest()
    r = conn().execute("SELECT body FROM api_cache WHERE url_hash=?", ("llm_" + key,)).fetchone()
    if r:
        return json.loads(r["body"])
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema,
                             **({"thinkingConfig": {"thinkingLevel": "low"}} if model.startswith("gemini-3") else {})},
    }
    try:
        resp = httpx.post(URL.format(model), json=body, headers={"x-goog-api-key": GEMINI_API_KEY}, timeout=timeout)
    except httpx.HTTPError as e:
        raise LLMError(str(e)) from e
    if resp.status_code != 200:
        raise LLMError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")
    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        out = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise LLMError(f"bad Gemini response: {resp.text[:300]}") from e
    conn().execute("INSERT OR REPLACE INTO api_cache (url_hash, url, fetched_at, status, body) VALUES (?,?,?,?,?)",
                   ("llm_" + key, f"gemini:{model}", now(), 200, json.dumps(out, ensure_ascii=False)))
    conn().commit()
    return out
