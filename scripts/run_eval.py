"""
run_eval.py — Run the verification agent against ground_truth_cases and report metrics (PRD §17).

By default only human-APPROVED/EDITED cases are scored. --include-pending scores PENDING cases too, and the report
is then clearly labelled "includes unreviewed cases" (useful during development, never for slides).

Outputs: eval_runs row, dataset/reports/evaluation_report.md, dataset/reports/failure_analysis.md,
         dataset/benchmark/eval_set.jsonl (approved cases only).
Usage: .venv/Scripts/python scripts/run_eval.py [--include-pending] [--split pilot|dev|test] [--offline]
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.agent.verify import verify  # noqa: E402
from backend.app.db import insert, new_id, now, rows  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ["VERIFIED", "CONFLICTING", "OUTDATED", "UNVERIFIED"]
CRITICAL = {("UNVERIFIED", "CONFLICTING"): "absence treated as contradiction",
            ("OUTDATED", "CONFLICTING"): "superseded treated as false",
            ("VERIFIED", "CONFLICTING"): "historically true treated as false"}


def failure_category(exp, pred, res):
    if exp == pred:
        return None
    n_ev = len(res.get("supporting_evidence", [])) + len(res.get("contradicting_evidence", []))
    if (exp, pred) in CRITICAL:
        return "contradiction failure" if exp == "UNVERIFIED" else ("temporal failure" if exp == "OUTDATED" else "contradiction failure")
    if not (res.get("geographic_analysis") or {}).get("resolved"):
        return "geographic failure"
    if exp in ("VERIFIED", "CONFLICTING") and n_ev == 0:
        return "retrieval failure"
    if exp == "OUTDATED" or pred == "OUTDATED":
        return "temporal failure"
    if exp == "UNVERIFIED":
        return "uncertainty failure"
    if exp == "CONFLICTING":
        return "contradiction failure"
    return "grounding failure"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-pending", action="store_true")
    ap.add_argument("--split", default=None)
    ap.add_argument("--offline", action="store_true", help="no live tool calls (cached evidence only)")
    a = ap.parse_args()
    decisions = ("APPROVE", "EDIT", "PENDING") if a.include_pending else ("APPROVE", "EDIT")
    sql = (f"SELECT g.*, c.claim_text, c.published_at FROM ground_truth_cases g JOIN claims c ON c.claim_id=g.claim_id "
           f"WHERE g.review_decision IN ({','.join('?' * len(decisions))})")
    params = list(decisions)
    if a.split:
        sql += " AND g.split=?"
        params.append(a.split)
    cases = rows(sql, params)
    if not cases:
        print("No cases to evaluate (approve cases with scripts/review_cases.py, or use --include-pending).")
        return
    results, conf = [], Counter()
    for g in cases:
        t = time.time()
        res = verify(g["claim_text"], g["published_at"], g["verification_context"], g["verification_time"],
                     persist=False, live=not a.offline)
        pred = res.get("status") or "UNVERIFIED"
        cat = failure_category(g["expected_status"], pred, res)
        conf[(g["expected_status"], pred)] += 1
        results.append({"case_id": g["case_id"], "context": g["verification_context"], "expected": g["expected_status"],
                        "predicted": pred, "expected_subtype": g["verification_subtype"],
                        "predicted_subtype": res.get("verification_subtype"), "failure": cat,
                        "critical": CRITICAL.get((g["expected_status"], pred)), "latency_s": round(time.time() - t, 2),
                        "explanation": res.get("explanation"), "review": g["review_decision"]})
        print(f"{g['case_id']:<28} exp {g['expected_status']:<11} pred {pred:<11} {'OK' if not cat else cat}")
    per = {}
    for s in STATUSES:
        tp = conf[(s, s)]
        fp = sum(conf[(e, s)] for e in STATUSES if e != s)
        fn = sum(conf[(s, p)] for p in STATUSES if p != s)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        per[s] = {"precision": round(pr, 3), "recall": round(rc, 3),
                  "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0, "support": tp + fn}
    present = [s for s in STATUSES if per[s]["support"]]
    metrics = {"n": len(results), "accuracy": round(sum(r["expected"] == r["predicted"] for r in results) / len(results), 3),
               "macro_f1": round(sum(per[s]["f1"] for s in present) / max(len(present), 1), 3),
               "per_status": per, "critical_errors": sum(1 for r in results if r["critical"]),
               "median_latency_s": sorted(r["latency_s"] for r in results)[len(results) // 2],
               "includes_unreviewed": a.include_pending}
    failures = Counter(r["failure"] for r in results if r["failure"])
    confusion = {e: {p: conf[(e, p)] for p in STATUSES} for e in STATUSES}
    insert("eval_runs", {"id": new_id("run_"), "created_at": now(), "split": a.split or "all",
                         "metrics": metrics, "confusion": confusion, "failures": dict(failures),
                         "config": {"include_pending": a.include_pending, "offline": a.offline, "cases": results}})
    rep = ROOT / "dataset" / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    warn = "\n> ⚠️ Includes cases NOT yet human-reviewed (development run). Do not quote on slides.\n" if a.include_pending else ""
    md = [f"# Evaluation report — {now()}", warn, f"Cases: {metrics['n']} · Accuracy {metrics['accuracy']} · "
          f"Macro-F1 {metrics['macro_f1']} · Critical errors {metrics['critical_errors']} · "
          f"Median latency {metrics['median_latency_s']} s", "", "| Status | P | R | F1 | n |", "|---|---|---|---|---|"]
    md += [f"| {s} | {per[s]['precision']} | {per[s]['recall']} | {per[s]['f1']} | {per[s]['support']} |" for s in STATUSES]
    md += ["", "## Confusion (rows = expected)", "| | " + " | ".join(STATUSES) + " |", "|---" * 5 + "|"]
    md += [f"| {e} | " + " | ".join(str(confusion[e][p]) for p in STATUSES) + " |" for e in STATUSES]
    md += ["", "## Cases", "| Case | Ctx | Expected | Predicted | Failure |", "|---|---|---|---|---|"]
    md += [f"| {r['case_id']} | {r['context']} | {r['expected']} | {r['predicted']} | {r['failure'] or ''} |" for r in results]
    (rep / "evaluation_report.md").write_text("\n".join(md), encoding="utf-8")
    fa = ["# Failure analysis", warn, *[f"- **{k}**: {v}" for k, v in failures.items()], ""]
    for r in results:
        if r["failure"]:
            fa += [f"## {r['case_id']} ({r['context']}) — expected {r['expected']}, got {r['predicted']}",
                   f"Category: {r['failure']}" + (f" · CRITICAL: {r['critical']}" if r["critical"] else ""), "",
                   "```", r["explanation"] or "", "```", ""]
    (rep / "failure_analysis.md").write_text("\n".join(fa), encoding="utf-8")
    approved = rows("SELECT g.*, c.claim_text, c.published_at, c.is_synthetic AS claim_synthetic FROM ground_truth_cases g "
                    "JOIN claims c ON c.claim_id=g.claim_id WHERE g.review_decision IN ('APPROVE','EDIT')")
    bdir = ROOT / "dataset" / "benchmark"
    bdir.mkdir(parents=True, exist_ok=True)
    with open(bdir / "eval_set.jsonl", "w", encoding="utf-8") as f:
        for r in approved:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(metrics, indent=1))
    print(f"eval_set.jsonl: {len(approved)} approved cases exported")


if __name__ == "__main__":
    main()
