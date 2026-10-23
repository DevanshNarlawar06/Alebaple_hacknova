# HACKNOVA'26 — Problem Statement Analysis & Decision

**Decision: PS-1 EnergyIQ.** Runner-up: PS-3 SquadSync. Third: PS-2 Disaster Verification.
Constraint: an 8–9 hour build, so this is a time-boxed analysis meant to support a decision, not a full study.

Labels used: **[OFFICIAL]** = stated in the HACKNOVA PDF/PPTX · **[VERIFIED]** = checked by us on 23 Oct 2026 · **[INFERENCE]** = our technical judgement · **[HYPOTHESIS]** = not yet validated.

---

## A. Source inventory

| File | Status |
|---|---|
| `HACKNOVA26_Problem_Statements.pdf` | 15 pages, all text extracted with PyMuPDF. Page images inspected: decoration only (logos, banners), no hidden tables. 5 problem statements (PS-1 … PS-5). |
| `HACKNOVA26_Final_Round_Presentation_Template.pptx` | 12 slides in file. Template slides 1–9 + "Thank You" = **10-slide maximum** [OFFICIAL]. File slide 10 is an empty blank and slide 12 is an instruction checklist that must be deleted before submission [OFFICIAL]. |

**Missing / ambiguous**
- PS-1 and PS-2 say that "synthetic" datasets are provided [OFFICIAL], but **none are in the workspace**. We use the public UCI datasets plus our own clearly labelled synthetic campus dataset. The app accepts any CSV, so the organiser data can be dropped in at the event.
- Team size and skills are not stated. We assume 2–4 students who know Python.
- No LLM API key is available in this environment [VERIFIED]. This matters for PS-2 and PS-4.

## B. Problem statements (condensed analysis)

### PS-1 EnergyIQ — Smart Energy Consumption Optimizer
- **Problem (plain terms):** A facility manager receives a meter reading curve. It shows *how much* energy was used, but not *whether that amount was abnormal*, *when the waste happened*, or *what to do about it*. Example: a hostel block draws 60% of its daytime load at 3 a.m. That is waste (equipment left on), and nobody notices because 3 a.m. is never a peak.
- **Mandatory [OFFICIAL]:** consumption analytics, peak-load analysis, anomaly detection, trend analysis, consumption drivers, a recommendation engine, an interactive dashboard, and a technical write-up. Recommendations must be grounded in observed data, and anomalies must be separated from normal variation.
- **Core technical challenge [INFERENCE]:** "Unusual" only makes sense against what is *expected for that hour, day and weather*. A global threshold flags every summer afternoon and misses a 3 a.m. baseload problem. The approach that works is a **counterfactual baseline model**: expected load = f(time, calendar, temperature). Residual = actual − expected. Anomalies are residuals that are large relative to the normal residual spread *for that context*.
- **Resources [VERIFIED]:** UCI Tetouan (52,416 rows, 10-min, 3 distribution zones + temperature/humidity/wind), UCI Appliances (19,735 rows, 10-min, one house + indoor/outdoor temperature), UCI Household (2M rows, 1-min). All three download freely (HTTP 200) under the CC BY 4.0 licence.
- **Hardest part:** proving that detection is *accurate* (evaluation criterion #2) without labelled anomalies. **Solution:** inject synthetic anomalies with known type and timing into real data, then measure precision, recall and F1, compared against naive detectors. Few teams will measure this.
- **Limitations:** We cannot see the physical cause (only patterns). Savings figures are estimates. Without sub-metering, "where" stops at the zone or meter level.
- **Feasibility:** High. Fully offline, no fragile API, and the team has prior energy-forecasting experience.

### PS-2 Disaster Information Verification Agent
- **Problem:** During a flood, a post says "Bridge X collapsed, NH-48 closed". Responders need to know whether it is current, whether it contradicts official alerts, and whether the place and time are consistent.
- **Mandatory:** claim extraction, source comparison, freshness, contradiction detection, geo-verification, a 4-way status (verified / conflicting / outdated / unverified), an evidence dashboard, and an **interactive map**.
- **Core challenge:** claim extraction and contradiction detection (NLI) need a strong language model. There is no LLM key here, so we would need local NLI models (e.g. DeBERTa-MNLI). These are CPU-feasible but weaker. GDACS has a public feed; the ReliefWeb API now requires an app name [HYPOTHESIS: not re-verified]. The synthetic data the PDF promises is not in the workspace.
- **Risk:** Highest judge appeal, but accuracy is hard to prove. Demo reliability depends on live feeds, and the risk of confidently wrong output is high.
- **Feasibility:** Medium-low in 8–9 hours without an LLM key.

### PS-3 SquadSync — Git and task-board collaboration risk
- **Problem:** Student teams find out about uneven workload, missing reviews or last-minute merges only at the deadline.
- **Mandatory:** ingestion and normalisation, workload, review participation, integration risk, justified indicators (not raw commit counts), evidence per risk, and a mentor view.
- **Core challenge:** choosing *justified* indicators: Gini of task points, review reciprocity, PR time-to-merge, branch age, the share of commits in the final 48 hours, and bus factor. Mostly deterministic analytics on GitHub REST data plus synthetic task data.
- **Risk:** Easy to build, so many teams will look similar. Most of the work is in the rules, with limited technical depth. GitHub REST needs a token for useful rate limits (unauthenticated: 60 requests/hour).
- **Feasibility:** High.

### PS-4 Meeting-to-Execution Automation Agent
- **Problem:** Action items get lost after meetings.
- **Mandatory:** extraction (decisions, owners, deadlines), commitment vs suggestion vs question classification, duplicate and conflict detection, an approval workflow, Trello or GitHub integration, and tracking.
- **Core challenge:** extraction quality depends on an LLM. Without a key, a rule-based or small-model version would score poorly on the official criterion #1 "accuracy of extraction". Trello needs API credentials.
- **Feasibility:** Medium. It is also likely the most popular choice, so differentiation is low.

### PS-5 Competitor Intelligence and Market Monitoring Agent
- **Problem:** Businesses miss competitor price and feature changes.
- **Mandatory:** monitoring, meaningful-change detection (not cosmetic DOM changes), dated history, configurable comparison, evidence-linked reports, alerts, and a demo with a simulated price change [OFFICIAL].
- **Core challenge:** semantic diffing (extracting structured price and feature fields, then diffing those fields rather than the HTML). Website terms of service and anti-bot measures make live scraping fragile, so the demo would use mock competitor pages anyway.
- **Feasibility:** Medium-high, but the "intelligence" layer is shallow without an LLM.

## C. Opportunities (baseline → differentiated → ambitious)

| PS | Baseline | Differentiated | Ambitious |
|---|---|---|---|
| PS-1 | Charts, a global z-score, top-N peaks, generic tips | **Weather- and calendar-aware counterfactual baseline. Anomalies classified by type. Every recommendation quantified (kWh, ₹, CO₂) and linked to evidence. Detection accuracy proven with an injection benchmark** | Online streaming detection plus closed-loop setpoint control |
| PS-2 | Keyword matching against alerts | Local NLI for contradictions, freshness decay, a geo-distance check, an evidence graph | Multi-agent live verification over GDACS, IMD and social feeds |
| PS-3 | Commit counts per person | Gini, review-reciprocity graph, integration-delay and bus-factor indicators, each with evidence | Predicting the risk of missing the deadline |
| PS-4 | Regex for "will / by Friday" | Small model plus rules, a dedup graph, an approval queue, GitHub Issues | Live meeting bot |
| PS-5 | HTML diff | Structured-field diff, significance scoring, sourced reports | Market-positioning NLP over announcements |

## D. Weighted scoring (1–10; weights from the master brief)

| Criterion (weight) | PS-1 | PS-2 | PS-3 | PS-4 | PS-5 |
|---|---|---|---|---|---|
| Official alignment (15) | 9 | 7 | 8 | 6 | 8 |
| Impact (15) | 8 | 9 | 6 | 7 | 6 |
| Technical depth (15) | 8 | 8 | 6 | 7 | 6 |
| Differentiation (15) | 7 | 8 | 6 | 5 | 6 |
| Feasibility in 9 h (15) | 9 | 5 | 9 | 6 | 7 |
| Data and validation (10) | 10 | 4 | 7 | 5 | 6 |
| Demo quality (10) | 8 | 8 | 7 | 7 | 7 |
| Reliability (5) | 9 | 5 | 8 | 6 | 6 |
| **Weighted /100** | **84.0** | **70.0** | **70.5** | **61.5** | **65.5** |

Rationale for the key scores:
- PS-1 has data and validation at 10 because real data is downloaded and accuracy is measurable.
- PS-2 has feasibility at 5 and data at 4 because there is no LLM key and the promised synthetic data is missing.
- PS-4 has alignment at 6 because extraction accuracy (its main criterion) needs an LLM we lack.

**Sensitivity:**
- If impact and differentiation are double-weighted: PS-1 81.9, PS-2 73.5, PS-3 68.1.
- If technical depth and differentiation are double-weighted: PS-1 81.9, PS-2 72.3.
- If feasibility is double-weighted: PS-1 84.8, PS-3 73.0, PS-2 67.4.
- PS-1 ranks first in every scenario. The runner-up flips between PS-2 and PS-3 depending on whether innovation or feasibility is weighted more heavily.
- If an LLM key becomes available, PS-2 and PS-4 each gain about 8–10 points. PS-2 would then become a close runner-up, but PS-1 would still lead on feasibility and data.

**Confidence:** high that PS-1 is the best choice under these constraints.

## E. Recommendation

1. **Winner: PS-1 EnergyIQ.** It is the only problem where the data is real and in hand, accuracy can be *measured*, and the demo needs no network. The evaluation criteria (insight quality, *accuracy* of anomaly and peak detection, data-grounded recommendations) reward exactly the counterfactual-baseline approach.
2. **Runner-up: PS-3 SquadSync.** Choose it if the judges are known to favour developer tools, or if the team has no data or analytics skills.
3. **Third: PS-2.** Choose it only if an LLM API key is available *and* the organisers supply the synthetic posts and alerts.

### Winning concept — "EnergyIQ WasteLens"
*"Shows facility managers not just how much energy they use, but how much they wasted, when, where, why, and what fixing it is worth."*

1. **Counterfactual baseline:** a LightGBM model of expected load (hour, weekday, month, holiday, temperature, humidity). It uses **out-of-fold** predictions, so every residual is honest (the model never saw the point it is judging).
2. **Context-aware anomaly detection:** a robust z-score of the residual, scaled by the normal residual spread *for that hour*, plus a persistence rule. Each event is classified as a **spike**, **sustained excess**, **after-hours waste** or **drop/outage**, with its excess kWh.
3. **Peak intelligence:** hour × weekday heatmap, load-duration curve, peak-to-average ratio, load factor, and each zone's share of the coincident peak.
4. **Driver analysis:** a change-point temperature model (balance point, kWh per °C), a baseload vs variable split, and weekend vs weekday ratio.
5. **Quantified recommendations:** each one carries its evidence metric, time window, estimated kWh, ₹ and CO₂ savings, and a confidence level.
6. **Validation lab (differentiator):** injects anomalies with known labels and reports precision, recall and F1 against naive global z-score and IQR detectors, alongside the baseline model's accuracy (MAPE, R²) on held-out data.

## F. Execution blueprint

- **Stack:** Python 3.12, pandas, LightGBM, Streamlit + Plotly (one process, offline-safe), and pytest for engine checks.
- **Layout:** `energyiq/` (engine: `ingest.py`, `baseline.py`, `anomaly.py`, `peaks.py`, `drivers.py`, `recommend.py`, `validate.py`), `app.py` (dashboard), `data/` (raw and synthetic), `scripts/` (synthetic generator), `tests/`.
- **Data flow:** CSV → ingest (auto-detect the timestamp, meter columns and weather columns; resample to hourly) → baseline (out-of-fold) → residuals → anomalies, peaks and drivers → recommendations → dashboard.
- **P0:** ingest + baseline + anomalies + peaks + recommendations + dashboard on Tetouan.
- **P1:** validation lab, synthetic campus dataset, CSV upload, what-if savings slider, report export.
- **P2:** live-stream simulation.
- **Acceptance:**
  - Runs end-to-end on all bundled datasets in under 60 seconds.
  - Injection-benchmark F1 beats the naive detectors.
  - Every recommendation shows its evidence numbers.
- **Fallbacks:** No network is needed at demo time; datasets are bundled. If the model fails, fall back to an hour × weekday median profile as the baseline.
- **Limitations to state:** savings are estimates using a configurable tariff (default ₹8/kWh) and grid emission factor (default 0.71 kg CO₂/kWh, based on the CEA India average; configurable). Pattern ≠ cause; a human must confirm the cause.

## G. Presentation outline (official template, 10 slides)

1. **Title:** EnergyIQ WasteLens · PS-1 · repo and demo links · team.
2. **Problem:** raw meter data hides waste. Global thresholds miss night baseload and flag every hot afternoon. Users: facility managers and campuses.
3. **Solution:** the counterfactual "expected vs actual" idea, the 5 features, and quantified recommendations.
4. **Workflow:** ingest → baseline (OOF LightGBM) → residual z-score → event typing → peaks and drivers → recommendations (flowchart).
5. **Architecture:** CSV/upload → engine modules → Streamlit UI; no external services.
6. **Tech stack:** pandas, LightGBM, Plotly, Streamlit, pytest; reasons for each choice.
7. **Prototype:** real screenshots (overview, anomaly band, recommendations, validation lab), clearly marked *implemented* vs *planned*.
8. **Feasibility and impact:** measured F1 vs naive detectors, baseline MAPE, and estimated savings on Tetouan (labelled as estimates); risks and mitigations.
9. **Extra:** validation-lab evidence and limitations.
10. **Thank You.**
