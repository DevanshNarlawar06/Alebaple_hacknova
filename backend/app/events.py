"""In-process pub/sub feeding the SSE stream (/api/stream)."""
from __future__ import annotations

import asyncio
import threading


class Bus:
    def __init__(self):
        self._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        with self._lock:
            self._subs.append((asyncio.get_running_loop(), q))
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs = [(l, x) for l, x in self._subs if x is not q]

    def publish(self, type_: str, data: dict):
        msg = {"type": type_, "data": data}
        with self._lock:
            subs = list(self._subs)
        for loop, q in subs:
            try:
                loop.call_soon_threadsafe(q.put_nowait, msg)
            except Exception:
                pass


bus = Bus()
