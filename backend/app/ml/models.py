"""Local models: multilingual NLI (stance) and multilingual embeddings. Lazy-loaded, GPU if available."""
from __future__ import annotations

import threading

import numpy as np

from ..config import EMBED_MODEL, NLI_MODEL, USE_NLI

_lock = threading.Lock()
_nli = None
_emb = None


def _device():
    try:
        import torch
        return 0 if torch.cuda.is_available() else -1
    except Exception:
        return -1


def nli_model():
    global _nli
    with _lock:
        if _nli is None:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            tok = AutoTokenizer.from_pretrained(NLI_MODEL)
            mdl = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL)
            dev = "cuda" if _device() == 0 else "cpu"
            mdl = mdl.to(dev).eval()
            if dev == "cuda":
                mdl = mdl.half()
            labels = {v.lower(): k for k, v in mdl.config.id2label.items()}
            _nli = (tok, mdl, dev, labels)
    return _nli


_nli_cache: dict[tuple[str, str], dict] = {}


def nli(pairs: list[tuple[str, str]]) -> list[dict]:
    """pairs of (premise, hypothesis) → [{'entailment','neutral','contradiction'}] probabilities (memoised)."""
    if not pairs or not USE_NLI:
        return [{"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0} for _ in pairs]
    todo = [pr for pr in dict.fromkeys(pairs) if pr not in _nli_cache]
    if todo:
        for pr, res in zip(todo, _nli_raw(todo)):
            _nli_cache[pr] = res
    return [_nli_cache[pr] for pr in pairs]


def _nli_raw(pairs):
    import torch
    tok, mdl, dev, labels = nli_model()
    out = []
    for i in range(0, len(pairs), 16):
        batch = pairs[i:i + 16]
        enc = tok([p for p, _ in batch], [h for _, h in batch], truncation=True, max_length=256,
                  padding=True, return_tensors="pt").to(dev)
        with torch.no_grad():
            probs = torch.softmax(mdl(**enc).logits.float(), dim=-1).cpu().numpy()
        for row in probs:
            out.append({k: float(row[labels[k]]) for k in ("entailment", "neutral", "contradiction")})
    return out


def embedder():
    global _emb
    with _lock:
        if _emb is None:
            from sentence_transformers import SentenceTransformer
            _emb = SentenceTransformer(EMBED_MODEL, device="cuda" if _device() == 0 else "cpu")
    return _emb


def embed(texts: list[str], kind: str = "query") -> np.ndarray:
    """multilingual-e5 expects 'query: ' / 'passage: ' prefixes; returns L2-normalised vectors."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    return embedder().encode([f"{kind}: {t}" for t in texts], normalize_embeddings=True,
                             batch_size=32, show_progress_bar=False).astype(np.float32)


def warmup():
    """Load both models once (server startup), so the first claim isn't slow."""
    embed(["warm up"])
    if USE_NLI:
        nli([("warm up premise", "warm up hypothesis")])
