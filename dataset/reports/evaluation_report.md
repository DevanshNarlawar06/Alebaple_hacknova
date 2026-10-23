# Evaluation report — 2026-10-23T12:01:59Z

> ⚠️ Includes cases NOT yet human-reviewed (development run). Do not quote on slides.

Cases: 7 · Accuracy 1.0 · Macro-F1 1.0 · Critical errors 0 · Median latency 8.35 s

| Status | P | R | F1 | n |
|---|---|---|---|---|
| VERIFIED | 1.0 | 1.0 | 1.0 | 3 |
| CONFLICTING | 1.0 | 1.0 | 1.0 | 1 |
| OUTDATED | 1.0 | 1.0 | 1.0 | 2 |
| UNVERIFIED | 1.0 | 1.0 | 1.0 | 1 |

## Confusion (rows = expected)
| | VERIFIED | CONFLICTING | OUTDATED | UNVERIFIED |
|---|---|---|---|---|
| VERIFIED | 3 | 0 | 0 | 0 |
| CONFLICTING | 0 | 1 | 0 | 0 |
| OUTDATED | 0 | 0 | 2 | 0 |
| UNVERIFIED | 0 | 0 | 0 | 1 |

## Cases
| Case | Ctx | Expected | Predicted | Failure |
|---|---|---|---|---|
| clm_pilot_001:HISTORICAL | HISTORICAL | VERIFIED | VERIFIED |  |
| clm_pilot_002:HISTORICAL | HISTORICAL | CONFLICTING | CONFLICTING |  |
| clm_pilot_003:HISTORICAL | HISTORICAL | VERIFIED | VERIFIED |  |
| clm_pilot_003:CURRENT | CURRENT | OUTDATED | OUTDATED |  |
| clm_pilot_004:HISTORICAL | HISTORICAL | UNVERIFIED | UNVERIFIED |  |
| clm_pilot_005:HISTORICAL | HISTORICAL | VERIFIED | VERIFIED |  |
| clm_pilot_005:CURRENT | CURRENT | OUTDATED | OUTDATED |  |