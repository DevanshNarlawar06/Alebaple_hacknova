"""
build_pilots.py — Rebuild the handover's 5 pilot cases on retrievable primary evidence (PRD §11.1).

- Registers pilot claims: real CrisisMMD tweets where the handover specified CrisisMMD material, plus two
  clearly-marked synthetic claims (is_synthetic=1).
- Fetches primary evidence: USGS FDSN events, NWS products (IEM AFOS archive).
- Writes PROPOSED ground_truth_cases with review_decision='PENDING'. Nothing is auto-approved:
  a human must APPROVE/EDIT/REJECT via scripts/review_cases.py before eval_set.jsonl includes them.

Usage: .venv/Scripts/python scripts/build_pilots.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.connectors import nws_afos, usgs  # noqa: E402
from backend.app.connectors.sources import ensure_sources  # noqa: E402
from backend.app.db import conn, insert, now, one  # noqa: E402

PILOTS = [
    dict(case="clm_pilot_001", real_claim="clm_efffe897d192", ctx=["HISTORICAL"], expected=["VERIFIED"],
         subtype=["FACTUAL_CONFIRMATION"], reasoning="Magnitude-7.1 earthquake in central Mexico on 19 Sep 2017 with "
         "building damage in Mexico City is confirmed by the USGS event record us2000ar20."),
    dict(case="clm_pilot_002", synthetic=True, posted_at="2017-09-20T02:10:00Z",
         text="BREAKING: a 12-metre tsunami has just smashed into Acapulco after the 7.1 earthquake, at least 300 dead "
              "on the beaches. Most terrifying thing I have ever seen.",
         ctx=["HISTORICAL"], expected=["CONFLICTING"], subtype=["POSITIVE_CONTRADICTION"],
         reasoning="USGS us2000ar20: epicentre inland (~236 km from Acapulco), tsunami flag 0. The tsunami proposition "
                   "is contradicted by positive physical evidence; the casualty figure stays UNVERIFIED (not "
                   "contradicted); the personal-experience sentence is SUBJECTIVE. Event-binding trap: us2000ahv0 "
                   "(8 Sep, offshore, tsunami flag 1) is a different event."),
    dict(case="clm_pilot_003", synthetic=True, posted_at="2017-09-23T13:30:00Z",
         text="URGENT: the Guajataca Dam is failing. Everyone in Isabela and Quebradillas must evacuate to higher "
              "ground immediately.",
         ctx=["HISTORICAL", "CURRENT"], expected=["VERIFIED", "OUTDATED"],
         subtype=["FACTUAL_CONFIRMATION", "SUPERSEDED_DIRECTIVE"],
         reasoning="NWS San Juan Flash Flood Emergency / Dam Failure warnings (22–24 Sep 2017) support the directive "
                   "at claim time; their validity windows ended on 24 Sep 2017, so in the CURRENT context the "
                   "directive is superseded (OUTDATED), not false."),
    dict(case="clm_pilot_004", real_claim="clm_a21b9961e358", ctx=["HISTORICAL"], expected=["UNVERIFIED"],
         subtype=["INSUFFICIENT_EVIDENCE"],
         reasoning="Harvey flooding in Houston is regionally confirmed, but the specific looting incident is neither "
                   "confirmed nor contradicted by an authoritative source → UNVERIFIED, never CONFLICTING."),
    dict(case="clm_pilot_005", real_claim="clm_e5e42f0e2d0f", ctx=["HISTORICAL", "CURRENT"],
         expected=["VERIFIED", "OUTDATED"], subtype=["HISTORICAL_SNAPSHOT", "SUPERSEDED_STATISTIC"],
         reasoning="M7.3 on 12 Nov 2017 confirmed by USGS us2000bmcg; 'at least 210 killed' matched contemporaneous "
                   "reports but was later revised upward (casualty provenance PROVISIONAL) → historically valid, "
                   "currently superseded."),
]


def main():
    ensure_sources()
    for eid in ("us2000ar20", "us2000ahv0", "us2000bmcg"):
        print("USGS", usgs.get_event(eid)["evidence_interpretation"][:100])
    nws = nws_afos.products("FFWSJU", "2017-09-22", "2017-09-24", keyword="Guajataca")
    print("NWS Guajataca products:", len(nws))
    c = conn()
    for p in PILOTS:
        if p.get("synthetic"):
            c.execute("""INSERT OR IGNORE INTO claims (claim_id, claim_text, source_id, source_type, published_at,
                         retrieved_at, event_type, is_synthetic, generation_method, channel, provenance)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                      (p["case"], p["text"], "src_synthetic", "synthetic", p["posted_at"], now(), "unknown", 1,
                       "hand-written pilot (handover design)", "replay",
                       json.dumps({"pilot": p["case"], "note": "synthetic claim; not a real post"})))
            cid = p["case"]
        else:
            cid = p["real_claim"]
            assert one("SELECT 1 FROM claims WHERE claim_id=?", (cid,)), cid
        for i, ctx in enumerate(p["ctx"]):
            insert("ground_truth_cases", {
                "case_id": f"{p['case']}:{ctx}", "claim_id": cid, "verification_context": ctx,
                "expected_status": p["expected"][i], "verification_subtype": p["subtype"][i],
                "reasoning": p["reasoning"], "is_synthetic": int(bool(p.get("synthetic"))),
                "provenance": json.dumps({"source": "handover pilot design, rebuilt on retrieved primary evidence",
                                          "pilot": p["case"]}),
                "verification_time": "2026-10-23T12:00:00Z", "review_decision": "PENDING", "split": "pilot"})
    c.commit()
    n = one("SELECT COUNT(*) n FROM ground_truth_cases WHERE split='pilot'")["n"]
    print(f"COMPLETED: {n} pilot cases written as PENDING (human review required)")


if __name__ == "__main__":
    main()
