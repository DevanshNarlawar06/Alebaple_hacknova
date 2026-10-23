"""Print a compact trace of one verification. Usage: python scripts/debug_case.py <case_id> | --text "..." [--ctx CURRENT]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.agent.verify import verify  # noqa: E402
from backend.app.db import one  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("case", nargs="?")
ap.add_argument("--text")
ap.add_argument("--posted")
ap.add_argument("--ctx", default="CURRENT")
ap.add_argument("--vt")
a = ap.parse_args()
if a.case:
    g = one("SELECT g.*, c.claim_text, c.published_at FROM ground_truth_cases g JOIN claims c USING(claim_id) WHERE case_id=?", (a.case,))
    text, posted, ctx, vt = g["claim_text"], g["published_at"], g["verification_context"], g["verification_time"]
    print("EXPECTED", g["expected_status"], g["verification_subtype"])
else:
    text, posted, ctx, vt = a.text, a.posted, a.ctx, a.vt
r = verify(text, posted, ctx, vt, persist=False)
print("STATUS", r.get("status"), r.get("verification_subtype"), "conf", r.get("confidence"), "latency", r.get("latency_s"))
for t in r.get("trace", []):
    print("  TRACE", json.dumps(t, ensure_ascii=False, default=str)[:400])
for p in r.get("atomic_propositions", []):
    print("  PROP", p["id"], p["state"], p.get("type"), p.get("materiality"), p.get("quantity"), "S", p.get("support"),
          "C", p.get("contra"), "stale", p.get("support_stale"), "|", p["text"])
for k in ("supporting_evidence", "contradicting_evidence", "superseded_or_stale_evidence"):
    for e in r.get(k, [])[:6]:
        print(f"  {k[:4].upper()} {e['proposition_id']} w={e['weight']} ent={e['entail']} con={e['contradict']} "
              f"{e['layer']} {e['temporal_relation']} | {e['reason']} | {(e['interpretation'] or e['excerpt'] or '')[:110]}")
print("  UNCERTAINTY", r.get("uncertainty"))
