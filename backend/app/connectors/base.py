"""HTTP fetch with response cache (api_cache table), per-host rate limits and offline snapshot mode."""
from __future__ import annotations

import calendar
import hashlib
import threading
import time
from urllib.parse import urlparse

import httpx

from ..config import SNAPSHOT_MODE, USER_AGENT
from ..db import conn, now

_MIN_GAP = {"sachet.ndma.gov.in": 2.0, "nominatim.openstreetmap.org": 1.1, "api.gdeltproject.org": 5.2, "news.google.com": 0.5}
_last: dict[str, float] = {}
_lock = threading.Lock()


class FetchError(Exception):
    pass


def _cache_get(url: str, max_age_s: float | None):
    h = hashlib.sha1(url.encode()).hexdigest()
    r = conn().execute("SELECT fetched_at, status, body FROM api_cache WHERE url_hash=?", (h,)).fetchone()
    if not r:
        return None
    if max_age_s is not None and not SNAPSHOT_MODE:
        age = time.time() - calendar.timegm(time.strptime(r["fetched_at"], "%Y-%m-%dT%H:%M:%SZ"))
        if age > max_age_s:
            return None
    return r["body"]


def fetch(url: str, *, max_age_s: float | None = 1800, headers: dict | None = None, timeout: float = 25) -> bytes:
    """GET with cache. max_age_s=None means cached forever (immutable historical records)."""
    cached = _cache_get(url, max_age_s)
    if cached is not None:
        return cached
    if SNAPSHOT_MODE:
        raise FetchError(f"snapshot mode: no cached copy of {url}")
    host = urlparse(url).netloc
    with _lock:
        gap = _MIN_GAP.get(host, 0)
        wait = _last.get(host, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
    try:
        r = httpx.get(url, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=timeout,
                      follow_redirects=True)
    except httpx.HTTPError as e:
        stale = _cache_get(url, None)
        if stale is not None:
            return stale
        raise FetchError(f"{url}: {e}") from e
    if r.status_code != 200:
        stale = _cache_get(url, None)
        if stale is not None:
            return stale
        raise FetchError(f"{url}: HTTP {r.status_code}")
    h = hashlib.sha1(url.encode()).hexdigest()
    conn().execute("INSERT OR REPLACE INTO api_cache (url_hash, url, fetched_at, status, body) VALUES (?,?,?,?,?)",
                   (h, url, now(), r.status_code, r.content))
    conn().commit()
    return r.content
