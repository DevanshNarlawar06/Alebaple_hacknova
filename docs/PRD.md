# PRD — SachVerify
### Disaster Information Verification Agent + "Beacon" verified-alert app
**HACKNOVA'26 · PS-2 · v1.2 · 23 Oct 2026**

> **v1.2 changes:**
> - The earlier team's handover is merged in (Option A).
> - Every official PS-2 resource is mapped and used (§10.0). NDMA access is solved via the SACHET CAP feed.
> - New method rules: absence of evidence ≠ contradiction; claims split into atomic facts (§7.3); a historical vs current context (§7.5); freshness from validity windows and superseding records, not fixed hours.
> - Two dataset tracks (§11): a human-reviewed benchmark of ~50 cases including the 5 rebuilt pilot cases, and separate demo scenarios.
> - Data model extended from handover schema v0.1 to v0.2, additively (§13).
> - Failure-category evaluation (§17).
> - See `docs/HANDOVER_STATE.md` for what the handover actually contains.

> **v1.1 changes:**
> - New: how posts reach us and which get checked (§6.0).
> - New: grouping posts into stories, so each story is verified once (FR-1b).
> - New: news triangulation across local, national and global sources, with the copied-source rule (§7.0).
> - Four new connectors (Google News RSS, YouTube channel RSS, Mastodon, GDELT), checked live.
> - Matching updates to the agent, database, API, folders, evaluation, timeline and demo.

> **One line:** SachVerify checks disaster claims from social media against official alerts, live weather and seismic data, location and time. Each claim gets a verdict (*verified / conflicting / outdated / unverified*) with its evidence. The **Beacon** app then sounds an alarm only for threats that have been verified, and tells people when a viral rumour is *not* real.

*"Sach"* means truth in Hindi.

---

## 1. Problem

During floods, cyclones, earthquakes and heatwaves, information spreads faster than it can be checked:

- **Recycled media:** a 2019 Kolhapur flood video is forwarded in 2026 as "today".
- **Wrong place:** a real alert for one district gets attributed to another city.
- **Conflicting numbers:** "300 mm rain", "dam burst" and "10,000 evacuated" disagree with official figures.
- **Stale truth:** a warning that expired 6 hours ago is still being shared.
- **Language gap:** rumours spread in Hindi, Marathi and Telugu; officials cross-check in English.

**Who is affected**
- Emergency responders and SDMA/DDMA control rooms, who triage hundreds of reports.
- Hospitals and NGOs, who must decide where to send resources.
- Citizens, who either panic at fakes or ignore real warnings because of alert fatigue.

**Why current tools fall short [our assessment]**
- Official alerts (NDMA SACHET) are authoritative but don't respond to rumours.
- Fact-checkers are manual and slow (hours to days).
- Social platforms don't geo-check or time-check claims against official feeds.

## 2. Goals, non-goals, success metrics

**Goals**
1. Meet every PS-2 requirement end-to-end (Phase 1).
2. Make every verdict explainable: evidence for and against, with source, timestamp, location and confidence.
3. Abstain honestly: when evidence is insufficient, say "unverified" with the reason.
4. Phase 2: an alarm app that beeps only on official or verified threats, plus a "don't panic" rumour check.

**Non-goals (for the hackathon)**
- Deepfake detection; geolocating a video from its pixels.
- Live scraping of X/Instagram/WhatsApp (paid or closed APIs, against their terms). We use replayed or synthetic posts and say so openly.
- Real SMS or push delivery to the public.

**Success metrics (measured, not claimed)**

| Metric | Target | How it's measured |
|---|---|---|
| Verdict macro-F1 (4 classes) | ≥ 0.80 | held-out test split of the labelled synthetic set (§11) |
| "Outdated" recall | ≥ 0.85 | same split; ablation with the freshness check disabled |
| False "verified" rate | ≤ 5% | share of claims that are really false or unverified but get labelled verified |
| Claim → verdict latency | ≤ 3 s per claim (GPU), ≤ 8 s (CPU) | timed in the eval script |
| Beacon false alarms in scenario replay | 0 | replay of 3 scenarios |
| Demo works offline | yes | snapshot mode with no network |

## 3. Requirement traceability (official → our build)

| # | Official requirement [PDF p.4–6] | Component | Acceptance test | Phase |
|---|---|---|---|---|
| R0 | *(Enabler)* Getting posts in + choosing which to check | `connectors/*`, `nodes/triage.py`, `nodes/cluster.py` | Non-claims (prayers, opinions) are filtered out with ≥ 85% precision; duplicate posts collapse into one story | 1 |
| R1 | Claim Extraction | `agent/nodes/extract.py` | Pulls hazard, place, time and quantity from EN/HI posts; field accuracy ≥ 85% on 50 labelled posts | 1 |
| R2 | Source Comparison (alerts, reports, weather, other) | `retrieve.py`, `connectors/*` | Each claim is compared across all 5 source layers (§7.0); it gets ≥ 1 candidate evidence item, or an explicit "no source in window" | 1 |
| R3 | Information Freshness | `freshness.py` | Uses CAP `expires`, `msgType=Update/Cancel` and source age; expired-only evidence → OUTDATED | 1 |
| R4 | Contradiction Detection | `stance.py` (NLI) + `numeric.py` | Detects text contradiction and numeric conflict (rain mm, magnitude) | 1 |
| R5 | Geographic Verification | `geo/polygons.py`, `geocode.py` | Point-in-polygon against the NDMA CAP polygon; distance to the GDACS/USGS point | 1 |
| R6 | Evidence-Based Verification | `evidence` table + `EvidencePanel` | Every verdict lists supporting and contradicting evidence with links and timestamps | 1 |
| R7 | Verification Status (4 classes) | `decide.py` | Deterministic decision table (§7.4) | 1 |
| R8 | Evidence Dashboard | `frontend/pages/Console` | Claims feed, filters, evidence and timestamps | 1 |
| R9 | Interactive Map | `components/MapView` | Claims coloured by status + alert polygons + quake points | 1 |
| R10 | Communicate uncertainty / no unsupported claims [Constraints] | `explain.py` + grounding guard | The explanation only cites evidence IDs; confidence and reason are always shown | 1 |
| R11 | Technical explanation deliverable | `docs/ARCHITECTURE.md`, slides | Written | 1 |
| M1 | *(Method)* Atomic propositions + exclusion of subjective content | `nodes/decompose.py`, `propositions` table | Proposition split matches the reviewed cases on ≥ 80% of material propositions | 1 |
| M2 | *(Method)* HISTORICAL vs CURRENT context; superseded information | `nodes/freshness.py`, `nodes/bind_event.py`, `verdicts.verification_context` | Pilots 003 and 005 give VERIFIED (historical) and OUTDATED (current) | 1 |
| M3 | *(Method)* Absence ≠ contradiction | `policies.py` rule 1 needs positive evidence | 0 UNVERIFIED→CONFLICTING critical errors on the test split | 1 |
| X1 | Beacon: location-aware verified alarm | `beacon/*`, `pages/Beacon` | Beeps only on RED; replay shows 0 false alarms | 2 |
| X2 | Rumour check ("don't panic") | `beacon/threat.py` | A contradicted or outdated viral claim near the user shows a green "not confirmed" card | 2 |
| X3 | Recycled-media check | `ml/phash.py`, `ml/vision.py` | A recycled image or keyframe is matched to an earlier first-seen date → OUTDATED | 3 |

## 4. Phased plan

- **Phase 1 — Official requirements (P0, must finish first).** Bring posts in (tipline + open feeds + replay) → check-worthiness filter → story grouping → extract, retrieve (official + sensors + local, national and global news), check, decide, explain → Console dashboard and map, plus evaluation.
- **Phase 2 — Beacon (P1, the idea that sets us apart).** A citizen web app (PWA): set your location, see a live threat level, hear an audible alarm with vibration and a browser notification on verified threats, and get rumour-check cards.
- **Phase 3 — Media verification (P1/P2).** Perceptual-hash recycled-media detection and CLIP scene consistency for images and video keyframes.
- **Stretch (P2).** A local-LLM explanation rewrite in the user's language; the ReliefWeb connector (once an app name is approved); a mobile push service worker over HTTPS.

**Gate:** Phase 2 starts only when the Phase 1 demo flow runs end-to-end.

## 5. Users and key flows

**Responder (Console, desktop)**
1. Opens the Console and sees the live claims feed with status badges and the map.
2. Clicks a claim → evidence panel: supporting and contradicting items, timestamps, a distance/inside-polygon check, freshness, NLI scores, confidence and a plain-language reason.
3. Filters by hazard, district, status or time; sees how verdicts change over time ("unverified → verified at 14:32 when the NDMA alert arrived").
4. Pastes or uploads a new post or image → verdict in seconds.

**Citizen (Beacon, mobile web)**
1. Allows location (or picks a city).
2. Sees a big status: 🟢 All clear / 🟡 Watch / 🔴 Alert, plus nearby verified items.
3. On 🔴: an alarm tone, vibration and a notification card ("Official NDMA flood alert covers your area until 17:30 — evidence").
4. Rumour card: "Viral 'Khadakwasla dam burst' video is from 2019 — not current. Official sources show no dam alert."

## 6. Functional requirements

### 6.0 How posts reach us, and which ones we check

**The constraint:** WhatsApp, Instagram and X are closed or paid, so we cannot see them. Tested on 23 Oct 2026: Reddit and Bluesky return 403 without a login; Mastodon's public API works. So we don't pretend to "monitor all social media". Posts reach us through three channels:

| Channel | How | Why it is realistic |
|---|---|---|
| **Tipline (push)** | A user forwards or pastes a post, link, screenshot or video into the Console or Beacon ("Is this real?") → `POST /api/tipline` | Rumours spread as forwards in closed groups; fact-checking tiplines work this way. The viral posts come to *us*. |
| **Open feeds (pull)** | Mastodon public hashtag and search timelines | Real, legal, timestamped public posts |
| **Scenario replay (demo / eval)** | Labelled synthetic + CrisisMMD-style posts on a replay clock | Measurable accuracy; clearly labelled synthetic |

**Post vs claim reliability.** We judge the **claim**, not the person. Forwards usually strip the author, so author signals (official handle, verified account) are a **weak prior** only: +0.1 credibility for official handles, 0 for unknown. A claim is never verified *because* of who posted it.

**FR-1 Ingestion**
- Connectors poll on a schedule (§10); raw payloads go to `api_cache`, parsed data to `alerts` / `observations` / `news_items` / `posts`.
- Posts enter through the three channels above.
- **Snapshot mode:** every connector can read from `data/snapshots/` so the demo runs without network.

**FR-1a Triage: which posts to check** (`nodes/triage.py`), in order, cheapest first:
1. **Language ID** (en/hi/mr/te + script check).
2. **Check-worthiness filter:** is it a *factual, checkable* disaster claim?
   - Must have: a hazard term (multilingual lexicon) **and** (a place **or** a time **or** a number).
   - Rejected as "not a claim": prayers, opinions, donation appeals, questions without an assertion. Example: "Stay safe Pune 🙏" is rejected; "Sinhagad Rd under 4 ft water" passes.
   - Method: rules first; a zero-shot NLI fallback ("This text reports a disaster event") for borderline cases.
3. **Priority score** = severity × spread × proximity:
   - **Severity:** lexicon weights; "dead", "dam burst", "evacuate" and "collapsed" score highest.
   - **Spread:** how many posts joined the story in the last 30 minutes.
   - **Proximity:** nearness to Beacon subscribers.

   Tipline submissions are always checked; the queue is processed highest priority first.

**FR-1b Story grouping** (`nodes/cluster.py`)
- Posts are embedded with multilingual-e5. A new post joins an existing story if cosine ≥ 0.82 **and** the hazard is the same **and** the place is within 25 km **and** the time is within 24 h. Otherwise it starts a new story.
- **The story is verified once; all its posts inherit the verdict.** 200 posts in 4 languages saying the same thing = 1 verification.
- Story fields: representative claim (the earliest, most specific post), first-seen time, post count, languages, and spread curve.
- Each independent post in a story is a weak corroboration signal (layer 5, §7.0). Near-duplicate copy-paste or forwards count once.

**FR-2 Claim extraction**
- Output schema `Claim{hazard, assertion, location_text, lat?, lon?, event_time?, quantities[{type,value,unit}], language, normalized_en}`.
- Method:
  - rules first: hazard keyword lexicon (EN/HI/MR), regex for numbers and units, `dateparser` for times ("kal raat", "2 hours ago"), gazetteer place matching;
  - the LLM fills gaps;
  - every extracted string must appear in the source post (grounding check), otherwise the field is dropped.

**FR-3 Geocoding**
- Order: gazetteer (GeoNames India, offline) → Nominatim (cached, 1 request/s) → leave unresolved (location uncertainty is recorded).
- Ambiguous names (several matches) are resolved using district or state context from the post; otherwise the claim is flagged `geo_ambiguous`.

**FR-4 Evidence retrieval** (across all 5 layers of §7.0)
- Candidate filter: same hazard family, spatial match (inside the polygon or within R_h km), and time window W_h.
- **News is searched on demand:** Google News RSS with `"<place> <hazard> when:2d"` in the claim's language **and** in English (hi/mr/en editions). Regional YouTube channel feeds are matched by place and hazard keywords in titles and descriptions.
- Ranking: cosine similarity with multilingual-e5 embeddings.
- Top-k = 5 per layer.
- **Copied-source rule:** news items with cosine ≥ 0.9 to each other (or the same agency byline) are grouped; only the **earliest publisher** counts as an independent source. The others are listed as "also reported by".

**FR-5 Checks (signals)**
- Stance (NLI, mDeBERTa-xnli)
- Numeric consistency
- Geo
- Freshness
- Source credibility
- Social corroboration (independent posts only; near-duplicates collapsed)
- Media (Phase 3)

**FR-6 Verdict + confidence** using the deterministic decision table (§7.4); thresholds calibrated on the development split.

**FR-7 Explanation**
- A template-built explanation that lists evidence IDs.
- Optional LLM rephrasing must keep every number and source exactly as given, otherwise the template text is used.

**FR-8 Re-verification (watcher agent)**
- When new alerts or observations arrive, claims from the last 48 h in that area are re-verified.
- Verdict history is stored and changes are pushed over SSE.

**FR-9 Console UI**
- Claims feed, evidence panel, map, filters, timeline, "check a post" box, evaluation page.

**FR-10 Beacon**
- Subscription by location → threat level computed per location → SSE push → alarm (Web Audio), vibration and Notification API.
- Acknowledge button; re-alert only on escalation; quiet de-duplication.

## 7. Verification methodology

### 7.0 Source layers: comparing local, national and global sources

A post's own timestamp is when it was *posted*, not when or where the event or video happened, and location tags are rare. So we extract the **claimed** place and time from the text (FR-2) and check them against independent layers:

| Layer | Sources | Strength | Weakness | Base trust |
|---|---|---|---|---|
| 1 Official | NDMA SACHET CAP (polygons, expiry), GDACS | Authoritative, exact area | Slower; covers broad areas | 1.0 / 0.95 |
| 2 Sensors | Open-Meteo, USGS | **Physical measurement: can't lie** | Says nothing about damage or roads | 0.9 / 0.95 |
| 3 Local news | Google News RSS by city in hi/mr/en; YouTube RSS of regional channels (configurable list, e.g. Lokmat, ABP Majha, TV9 Marathi, Pudhari) | **Fastest and most local**; covers street-level detail | Can be early and wrong; fewer editorial checks | 0.65 + up to 0.1 for being near the event |
| 4 National / global | NDTV, Times of India, DD News (YouTube/RSS); GDACS; GDELT | Editorial checks; shows scale | Later; less local detail | 0.75 |
| 5 Other posts | Independent posts in the same story | Volume and early signal | Easy to fake or copy | 0.25 each, max 3 |

**How the layers combine:**
1. **Independence:** only *independent* sources add up. Copied wire stories count once (FR-4). Posts that are forwards of each other count once (FR-1b).
2. **Agreement across layers:** support from two or more different layers (e.g. local news + sensor) gets a ×1.2 bonus on S. Support from a single layer gets none. Five copies of local news are weaker than one local report plus one rain-gauge reading.
3. **Timing (`nodes/timing.py`):**
   - For a real current event, local reports appear within hours of the posts. National or global coverage follows.
   - If the only matching coverage is about a **past, ended event** (event binding + validity window, §7.5), not merely "old", the claim is OUTDATED (RECYCLED_CONTENT).
   - If the post claims something *before* any source could know it, that adds no evidence by itself; it stays UNVERIFIED until a source appears. The watcher re-checks it later (FR-8).
4. **Detail contradiction:** local news says "waterlogging on Sinhagad Rd" but the post says "dam burst". NLI and numeric checks produce **CONFLICTING**, and the UI shows both quotes side by side.
5. **Sensor sanity check for media:** a video claiming torrential rain in place X on day D, while Open-Meteo shows < 2 mm there that day, is flagged "media inconsistent with weather". The video itself can't be geolocated in 8 hours, but this check is cheap and strong.
6. **Live TV:** transcribing live streams is out of scope (time). We use video **titles and descriptions** from regional channels' YouTube feeds, which update within minutes. Stretch goal: Whisper-small on a 60-second clip.

### 7.1 Hazard routing (agent chooses tools by hazard)
| Hazard | Evidence tools called |
|---|---|
| Flood / heavy rain / landslide | NDMA CAP, GDACS FL, Open-Meteo precipitation (past 72 h + forecast), local + national news, incident reports |
| Cyclone / storm / wind | NDMA CAP, GDACS TC, Open-Meteo wind/pressure, local + national news |
| Earthquake | USGS feed (magnitude, location), GDACS EQ, NDMA CAP, national news |
| Heatwave | NDMA CAP, Open-Meteo max temperature, local news |
| Fire / collapse / other | NDMA CAP, local news, incident reports, other posts. With no official or sensor layer, the claim can reach VERIFIED only with ≥ 2 independent news sources. |

### 7.2 Signal definitions (one evidence item e for one atomic proposition p)
- **Credibility** `cred(e)`: from the §7.0 layer table, plus official incident report 0.9 and NGO 0.6. Only independent sources count (copied items collapse to 1). Evidence with `provenance_status = PROVISIONAL` is capped at 0.7.
- **Operational validity, not age (adopted from the handover).** Each evidence item has a validity window `[valid_from, valid_until]`:
  - **Taken from the source wherever possible:** CAP `effective`/`expires`, `msgType=Update/Cancel` + `references`, GDACS `iscurrent`/`todate`, an all-clear notice, a revised situation report, or a final official count that replaces an interim one.
  - **There is no rule like "older than 24 h means outdated".**
  - Evidence that a later item replaces gets `superseded_by = <evidence_id>`.
  - `valid(e, t) = 1` if t is inside the window and nothing has superseded it, otherwise 0.
  - A mild age decay `exp(-Δt/τ_h)` is used **only to rank** evidence that has no validity information. It never decides OUTDATED by itself.
- **Geo** `geo(e)`: 1.0 if inside the CAP polygon; otherwise `exp(-d / D_h)` (D: flood 15 km, earthquake 150 km, cyclone 100 km). **Coordinates are never invented.** An unresolved or low-precision location gives `geo = null`, which the uncertainty note reports, and the geo check is skipped rather than guessed.
- **Stance**: NLI over (evidence text as premise, proposition as hypothesis) → p_ent, p_con, p_neu. Numeric checks override: claimed 300 mm vs observed 40 mm → p_con = 0.9; within ±35% → p_ent = 0.8.
- **Weight** `w(e) = cred · geo` (geo = 1 when not applicable, e.g. a national casualty figure).
- **Per proposition:** `S_p = Σ w·p_ent` and `C_p = Σ w·p_con`, computed over evidence **valid in the chosen verification context** (§7.5). If support comes from ≥ 2 different layers: `S_p ← 1.2·S_p`.

### 7.3 Atomic propositions (adopted from the handover)
Each claim is split into **atomic propositions**:
- *"Flooding has affected Area X since 6 PM and 500 people have been evacuated"* becomes:
  - a1 = flooding occurred in Area X
  - a2 = flooding began by 6 PM
  - a3 = 500 people were evacuated

Each proposition has:
- a `type`: event / location / time / quantity / casualty / directive / damage / other;
- a `materiality` flag: **core** = the event happened at that place and time; **detail** = everything else;
- a `factuality` flag: **FACTUAL**, **SUBJECTIVE** or **NON_FACTUAL**. *"Most violent earthquake I've ever felt"* is SUBJECTIVE. Subjective and non-factual propositions are shown but **excluded from aggregation**.

**Proposition state:**
| State | Rule |
|---|---|
| SUPPORTED | S_p ≥ θ_v ∧ C_p < θ_c |
| CONTRADICTED | C_p ≥ θ_v **from positive evidence** (a measurement, an official statement, an epicentre or location that makes it physically impossible). Absence of evidence never counts. |
| SUPERSEDED | Supported only by evidence that was valid at claim time but has since been replaced (revised count, lifted order, all-clear) |
| UNVERIFIED | Otherwise (with a reason code) |
| NON_FACTUAL / SUBJECTIVE | Excluded |

### 7.4 Claim status: aggregation rules (top to bottom; the epistemic rule is built in)
| # | Condition over the **factual** propositions | Status | Subtype examples |
|---|---|---|---|
| 1 | Any **core or detail** proposition is CONTRADICTED by positive evidence | **CONFLICTING** | POSITIVE_CONTRADICTION, NUMERIC_CONFLICT, GEOGRAPHIC_MISMATCH, TEMPORAL_MISMATCH, SOURCE_DISAGREEMENT (credible sources contradict *each other*) |
| 2 | (CURRENT context) The material propositions were SUPPORTED at claim time but are now SUPERSEDED, or the claim's event or media predates the post (timing check, recycled media) | **OUTDATED** | SUPERSEDED_DIRECTIVE, SUPERSEDED_STATISTIC, RECYCLED_CONTENT |
| 3 | All factual propositions SUPPORTED | **VERIFIED** | FACTUAL_CONFIRMATION, MULTI_SOURCE_CONFIRMATION, HISTORICAL_SNAPSHOT (in HISTORICAL context) |
| 4 | Core SUPPORTED but ≥ 1 detail UNVERIFIED | **UNVERIFIED** | PARTIALLY_SUPPORTED: the UI says "the flood is confirmed; the reported crime is not confirmed" |
| 5 | Otherwise | **UNVERIFIED** | INSUFFICIENT_EVIDENCE, LOCATION_UNRESOLVED, NO_SOURCE_COVERAGE |

- **Epistemic rule:** "no official report found" is never turned into "it did not happen". Rule 1 needs *positive* contradicting evidence; anything else falls through to UNVERIFIED.
- **Confidence** = `|S − C| / (S + C + 0.5)` averaged over material propositions → Low (< 0.3), Medium or High (> 0.6). Thresholds θ_v = 0.6 and θ_c = 0.3 to start, tuned on the development split.
- The **uncertainty list** is always returned: unresolved location, provisional provenance, unverified details, single-layer support, and model disagreement.

### 7.5 Verification context and the four timestamps (adopted from the handover)
- **Context:**
  - **HISTORICAL:** "was this true when it was said?" Uses evidence valid at `claim_time`.
  - **CURRENT:** "is this true and actionable now?" Uses evidence valid at `verification_time`.
  - The same claim can be **VERIFIED (historical) and OUTDATED (current)**. That is not a contradiction.
  - The Console shows both; Beacon always uses CURRENT.
- **Timestamps tracked:** `claim_time` (posted), `event_time` (claimed), `evidence_published_at`, `verification_time`.
- **How each evidence item relates to the claim in time:** *before the claim* · *at the same time* · *after the claim* · *superseding the claim* · *historically valid but now stale*.
- **Event binding:** a claim is tied to a specific event (by hazard + place + time) before evidence is compared. Example: a "Mexico earthquake tsunami" claim from 20 Sep 2017 binds to the **19 Sep Puebla** event (inland, no tsunami), **not** the 8 Sep Tehuantepec event (which did cause a tsunami). Binding failures are logged as a failure category (§17).

## 8. Agentic design

**Choice:** a bounded **state-graph agent** written in plain Python (async). Tools are typed functions; the LLM is used only at two narrow points (extraction gap-filling and explanation rephrasing). We do **not** use a free-form ReAct loop.

**Why not a free-form LLM agent?**
- On a 3B–7B local model it is slow and unpredictable.
- It can invent evidence, which PS-2 forbids.
- Results would not be reproducible for evaluation.

Judges get real agent behaviour (tool routing, an evidence-expansion loop, autonomous re-verification) with deterministic, auditable outcomes.

```
            ┌────────────┐
 post ───▶  │   triage   │  language → worth checking? → priority (FR-1a); not a claim → archive
            └─────┬──────┘
                  ▼
            ┌────────────┐
            │  cluster   │  join an existing story or start a new one (FR-1b);
            └─────┬──────┘  story already verified + no new evidence → reuse verdict
                  ▼
            ┌────────────┐
            │  extract   │  rules + LLM gap-fill + grounding guard
            └─────┬──────┘
                  ▼
            ┌────────────┐
            │ decompose  │  atomic propositions: type · core/detail · FACTUAL/SUBJECTIVE (§7.3)
            └─────┬──────┘
                  ▼
            ┌────────────┐
            │  geocode   │  gazetteer → Nominatim → ambiguity flag (never invents coordinates)
            └─────┬──────┘
                  ▼
            ┌────────────┐
            │ bind_event │  tie the claim to a specific event (hazard + place + time); log ambiguity
            └─────┬──────┘
                  ▼
            ┌────────────┐   chooses tools by hazard (§7.1)
            │   route    │──────────────────────────────┐
            └─────┬──────┘                              │
                  ▼                                     │
            ┌────────────┐   if 0 evidence: widen R,W   │
            │  retrieve  │◀── once (max 1 retry) ───────┘
            └─────┬──────┘   5 layers; on-demand news search; copied-source rule
                  ▼
   ┌────────┬─────────┬────────┬──────────┬────────┬──────────┐
   │ stance │ numeric │  geo   │freshness │ timing │ media(P3)│  run in parallel
   └───┬────┴────┬────┴───┬────┴────┬─────┴───┬────┴────┬─────┘
       └─────────┴────────┴────┬────┴─────────┴─────────┘
                        ▼
                 ┌────────────┐
                 │   decide   │  decision table §7.4
                 └─────┬──────┘
                       ▼
                 ┌────────────┐
                 │  explain   │  template (+ optional LLM rephrase, grounding-checked)
                 └─────┬──────┘
                       ▼
                 verdict + evidence ─▶ DB ─▶ SSE ─▶ Console / Beacon
```

**Agents (long-running workers)**
| Agent | Trigger | Job |
|---|---|---|
| Ingestor | APScheduler (§10 cadence) | Poll connectors (official, sensors, news, Mastodon), normalise, apply the copied-source rule, store, emit `new_evidence` |
| Verifier | new post / tipline / API call | Run the graph above, highest-priority stories first |
| Watcher | `new_evidence` event | Re-verify affected stories (same area, last 48 h), so an UNVERIFIED claim can become VERIFIED when local news or an official alert arrives; emit status changes |
| Beacon | status change / new official alert | Recompute threat per subscription; push alarm if level escalates |

**Tool interface** (`agent/tools.py`, all cached and with timeouts):
- `get_cap_alerts(bbox, since)`
- `get_cap_polygon(id)`
- `get_gdacs_events(type, bbox, since)`
- `get_usgs_quakes(bbox, since, minmag)`
- `get_weather(lat, lon, start, end, vars)`
- `search_news(query, lang, since)` → Google News RSS (hi/mr/en editions)
- `get_channel_feed(channel_id, since)` → YouTube channel RSS (regional + national)
- `search_mastodon(tag_or_query, since)`
- `search_gdelt(query, timespan)` → throttled to 1 request every 5 s
- `geocode(text, context)`
- `search_reports(query_vec, bbox, window)`
- `nli(premise, hypothesis)`
- `media_fingerprint(path)`

**Guardrails**
- JSON schema validation on all LLM output.
- Grounding check: extracted spans must be substrings of the post; explanation numbers must exist in the evidence.
- Timeouts → fallback to rules only.
- Max 1 retrieval expansion.
- Every verdict stores its full trace (`verdicts.trace_json`) for the "why" view.

## 9. ML and model choices

| Task | Primary | Fallback | Why | Size / VRAM |
|---|---|---|---|---|
| Stance / contradiction (NLI) | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (EN only) | Multilingual NLI: a Hindi claim vs an English alert works directly | ~280M params, ~0.6 GB fp16 |
| Semantic retrieval / dedup | `intfloat/multilingual-e5-small` | `paraphrase-multilingual-MiniLM-L12-v2` | Strong cross-lingual retrieval, small, fast | ~120M, ~0.3 GB |
| Claim extraction, atomic decomposition, explanation | **Gemini Flash** (key exists in the handover `.env`; *untested*) with JSON-schema output | Local **Ollama `qwen2.5:3b-instruct`** (Q4); rules-only if both are unavailable | Gemini: best quality for decomposition and Hindi/Marathi. Local: offline demo, no data leaves the laptop. **Same grounding guard on both** | Gemini: none locally · Qwen ~2.3 GB |
| Language ID | `langdetect` (+ script check for Devanagari/Telugu) | — | Tiny | — |
| Time parsing | `dateparser` (supports Hindi) | regex | Handles relative times | — |
| Geo | `shapely` point-in-polygon; haversine | — | Exact check against NDMA polygons | — |
| Recycled media (P3) | `imagehash` pHash + dHash; OpenCV keyframes every 2 s | — | Near-duplicate detection survives re-encoding, crops and watermarks | CPU |
| Scene consistency (P3) | `openai/clip-vit-base-patch32` zero-shot ("flood", "fire", "collapsed building", "normal street") | — | Checks that the image shows what the caption claims | ~0.6 GB |

**VRAM budget (6 GB):** NLI 0.6 + e5 0.3 + CLIP 0.6 + Qwen-3B 2.3 ≈ **3.8 GB** ✅. Use the 7B model only with CLIP unloaded.

**Training:** none (zero-shot plus calibrated thresholds). This is deliberate: there is no labelled in-domain training data, and calibrating on the development split is honest and fast.

## 10. Data sources and API choices (checked live on 23 Oct 2026)

### 10.0 Official PS-2 resources: all of them are used
The PDF (p.5) lists these resources. The judging criterion "reliability and grounding of sources" rewards building on them, so they are the **backbone**. Our extra sources (Open-Meteo, USGS, news, Mastodon) are allowed by the PDF's last bullet ("Teams may use … publicly available datasets, official alerts, news reports …") and are always labelled as additional.

| Official resource | Role in SachVerify | Status today | Action |
|---|---|---|---|
| **Synthetic social-media posts** (organiser-provided) | Main claim input for demo + evaluation | **Not received yet**; not in the workspace or the handover zip | Loader with column mapping (`connectors/organiser_data.py`) ready at hour 0; our own labelled scenario generator is the fallback and runs in addition |
| **Synthetic alerts, incident reports, timestamps, source metadata** (organiser-provided) | Evidence for the synthetic posts; tests freshness and contradiction | **Not received yet** | Same loader → `evidence` rows with `is_synthetic=1` |
| **CrisisMMD** | Real disaster tweets (2017) → claim pool for the benchmark (historical context), plus images for the media check | ✅ Text split files in the handover zip (16,058 tweets already in `evidence.db`); images not included | Fix geo-precision (§13 migration); download images only if Phase 3 is reached |
| **GDACS** | Official global events with points, bounding boxes, alert levels | ✅ RSS live (294 items) + downloader + snapshot in the handover repo | Keep; add CAP links; convert dates to ISO |
| **ReliefWeb** | Situation reports → evidence for current and historical events (incl. superseding reports and revised counts) | ⚠️ Our test: 403 without an approved app name. The handover `.env` **has an app name set** (untested) | Test with one request once you allow it. If it's rejected, request approval and use cached reports |
| **NDMA India** | Official Indian alerts: the primary trigger for Beacon and the main "Official" layer | ✅ **Solved:** NDMA's own SACHET CAP feed is a public, structured, official feed (RSS → CAP XML → polygons). No scraping of ndma.gov.in needed. This resolves the handover's open item PMA-004 | Connector `ndma_cap.py`; log the decision in `human_decisions.csv` |

**Extra sources (allowed by the PDF's last bullet):**
- USGS (earthquake facts; also the primary record for pilots 001, 002 and 005)
- Open-Meteo (rainfall and temperature checks)
- NWS text archive via the Iowa Environmental Mesonet (pilot 003)
- Google News RSS and YouTube channel RSS (local and national news)
- Mastodon (open social)
- GeoNames and Nominatim (geocoding)

| Source | Endpoint | Status | Use | Poll | Licence / terms |
|---|---|---|---|---|---|
| **NDMA SACHET CAP** | `sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml` → `FetchXMLFile?identifier=` → `FetchPolygonXMLFile?identifier=` | ✅ live, 100 items, CAP 1.2 with `event, urgency, severity, certainty, effective, onset, expires, msgType, areaDesc`, multilingual `info` blocks, **real polygons** | Primary official evidence + Beacon trigger | 2 min | Public government alerts |
| **GDACS** | `gdacs.org/xml/rss.xml` | ✅ 294 items; `eventtype, alertlevel, point, bbox, fromdate/todate, iscurrent, severity, country`, CAP link | International / large events (FL, TC, EQ, DR, WF) | 10 min | Public (EC JRC / UN OCHA) |
| GDACS JSON API | `/gdacsapi/api/events/geteventlist/...` | ❌ timed out | — (use RSS) | — | — |
| **USGS** | `earthquake.usgs.gov/.../summary/4.5_week.geojson` (+ `all_day`) | ✅ | Earthquake magnitude, location, time | 5 min | Public domain |
| **Open-Meteo** | `api.open-meteo.com/v1/forecast?past_days=3&hourly=precipitation,...` | ✅ no key | Measured/forecast rain, wind, temperature at the claim's location | on demand, cached 30 min | CC BY 4.0, free for non-commercial use |
| **Nominatim** | `nominatim.openstreetmap.org/search` | ✅ | Geocoding fallback | on demand, ≤ 1 req/s, cached forever | ODbL; usage policy needs a user agent |
| GeoNames India dump | `download.geonames.org/export/dump/IN.zip` | not yet downloaded | Offline gazetteer (primary geocoder) | once | CC BY 4.0 |
| ReliefWeb v2 | `api.reliefweb.int/v2/reports?appname=` | ❌ 403 without an approved app name (v1 shut down) | Optional situation reports | — | Request an app name; Phase 3 stretch |
| CrisisMMD v2 | `crisisnlp.qcri.org/crisismmd` | ✅ page up | Realistic post text and images for the synthetic set | once | Research use, cite the paper |
| **Google News RSS** | `news.google.com/rss/search?q=<place>+<hazard>+when:2d&hl={en-IN,hi,mr}&gl=IN` | ✅ 100 items per query in EN and HI, with publisher + `pubDate` | Layer 3/4 news: local (city query, regional language) and national | on demand per claim + every 10 min for active stories | Headlines and links only; we link to the original, no full-text copying |
| **YouTube channel RSS** | `youtube.com/feeds/videos.xml?channel_id=` | ✅ NDTV feed returned items timestamped within the hour; no key | Regional and national TV: titles and descriptions of news clips | 5 min | Public feed; metadata only |
| **Mastodon** | `mastodon.social/api/v1/timelines/tag/{tag}` | ✅ public, timestamped posts (few Indian posts) | Open social pull channel | 5 min | Public posts; author handles hashed |
| **GDELT DOC 2.0** | `api.gdeltproject.org/api/v2/doc/doc?mode=artlist&format=json` | ⚠️ works, but 429 above 1 request / 5 s | National/global news search with source country | throttled, on demand | Free; rate limit respected |
| Reddit / Bluesky | `reddit.com/search.json` · `public.api.bsky.app` | ❌ 403 without auth | — (Reddit OAuth app possible later) | — | — |
| X / Instagram / WhatsApp | — | ❌ paid or closed | — → **tipline** (users forward posts to us) + scenario replay | — | Stated openly in the demo |

## 11. Datasets: benchmark (evaluation) + scenarios (demo)

Two separate tracks, so the demo never leaks into the evaluation.

### 11.1 Track A — Evidence-grounded benchmark (adopted from the handover; ~50 human-approved cases)

```
Validated evidence  →  Candidate claims (150–250)  →  Atomic decomposition  →  Evidence linking
      →  Proposed status + reasoning  →  HUMAN REVIEW (APPROVE / EDIT / REJECT)  →  ~50 cases  →  eval_set.jsonl
```

**Evidence.** Every record keeps `raw_evidence_text`, `source_url`, `source_document_id`, `retrieved_at`, `evidence_hash` and `provenance_status`. No evidence is synthesised to fit a case. The handover's rejected tide-gauge record stays rejected.

**Claims.** Three kinds, each labelled with its origin:
1. **Real:** CrisisMMD tweets (2017: Harvey, Irma, Maria, Mexico earthquake, Iran-Iraq earthquake, California wildfires, Sri Lanka floods).
2. **Organiser-provided synthetic posts** (when released).
3. **Our controlled synthetic claims** for edge cases: geographic or temporal mismatch, numeric conflict, hyper-local rumour, superseded directive. Always marked `is_synthetic=1`.

**The 5 pilot cases**, rebuilt on primary records we have retrieved (see `HANDOVER_STATE.md` §8):
| Case | Context | Expected | Subtype | Primary evidence (retrieved) |
|---|---|---|---|---|
| `clm_pilot_001` Puebla quake report | HISTORICAL | VERIFIED | FACTUAL_CONFIRMATION (subjective part excluded) | USGS `us2000ar20` |
| `clm_pilot_002` "12 m tsunami at Acapulco" (synthetic) | HISTORICAL | CONFLICTING | POSITIVE_CONTRADICTION | USGS `us2000ar20`: inland epicentre 236 km from Acapulco; `tsunami=0` is only a supporting flag. The casualty figure stays UNVERIFIED, not contradicted. **Event-binding trap:** `us2000ahv0` (8 Sep) did cause a tsunami |
| `clm_pilot_003` Guajataca Dam evacuation | CURRENT | OUTDATED | SUPERSEDED_DIRECTIVE | NWS San Juan FFW "Flash Flood Emergency / Dam Failure", 23 Sep 2017 (IEM AFOS `FFWSJU`) + the superseding USACE record (to retrieve; the corrected interim-vs-permanent timeline is kept) |
| `clm_pilot_004` Harvey crime rumour | HISTORICAL | UNVERIFIED | INSUFFICIENT_EVIDENCE (PARTIALLY_SUPPORTED: flooding confirmed) | Regional flood evidence (NWS/USGS; to retrieve) |
| `clm_pilot_005` Iran-Iraq early casualty count | HISTORICAL / CURRENT | VERIFIED / OUTDATED | HISTORICAL_SNAPSHOT / SUPERSEDED_STATISTIC | USGS `us2000bmcg` (event facts); interim and final counts `PROVISIONAL` |

**Coverage target** (quality over balance; the counts are targets, not quotas):
- Statuses: VERIFIED ~14 · CONFLICTING ~12 · OUTDATED ~10 · UNVERIFIED ~14.
- Each of these appears **≥ 2 times**: historical snapshot, superseded statistic, superseded directive, positive contradiction, insufficient evidence, geographic mismatch, temporal mismatch, numeric inconsistency, source disagreement, mixed claim, subjective content, incomplete evidence, multi-source support, recycled content.
- **≥ 10 India cases** use NDMA CAP / GDACS / IMD-era evidence, so the benchmark is not US-only.

**Human review gate.** `scripts/review_cases.py` serves a local review page per candidate:
- claim → propositions → evidence for / against → time analysis → geo analysis → proposed status + reason;
- buttons: **APPROVE / EDIT / REJECT**.

Only APPROVED or EDITED cases go into `ground_truth_cases`. Every decision is logged to `human_decisions.csv`. **Generated cases are never auto-promoted.**

**Overfitting guard.** No `claim_id → answer` lookups and no phrase → status rules in the engine. A CI test greps the engine code for benchmark claim IDs. Thresholds are tuned on a 40% dev split only; the 60% test split is touched once per release.

**Gemini.** If the key test passes, Gemini proposes atomic decompositions and evidence links for *candidates only*. A human still approves each case, and the engine itself never sees Gemini's labels.

### 11.2 Track B — Live demo scenarios (synthetic, India-focused; labelled by construction)
`scripts/make_synthetic.py` generates replayable scenarios with ground truth. **These are never mixed into Track A.**

| Scenario | Content | Statuses covered |
|---|---|---|
| S1 Pune flash flood (2026-sim) | CAP-style alert (Pune polygon), Open-Meteo heavy rain, 25 posts EN/HI/MR | verified, conflicting (wrong numbers), unverified (other suburbs, hyper-local detail) |
| S2 Recycled Kolhapur flood (2019 media, 2026 posts) | No current alert; 2019 coverage only | outdated (recycled content) |
| S3 Odisha cyclone (sim) | GDACS TC + CAP Alert → **Update** moving the landfall area | historical verified → current outdated (superseded); conflicting landfall claims |
| S4 Delhi earthquake rumour | USGS-style M3.1 vs claim "M6.8, buildings collapsed" | conflicting (positive numeric contradiction) |
| S5 Noise | Prayers, opinions, donation appeals | not a claim (triage) |

- **Per scenario:** local-language and national news items, including copied wire stories, one early-but-wrong local report, and 2019 coverage for S2.
- **Triage set:** about 60 `not_a_claim` posts + near-duplicate forwards with story labels.
- **The organisers' synthetic posts and alerts**, once released, go into **both** tracks: raw into Track B replay; reviewed candidates into Track A.

## 12. Architecture and tech stack

Full diagram: [architecture.svg](architecture.svg) (also used on the Architecture slide).

```
┌──────────────────────── Frontend (React + Vite) ──────────────────────────┐
│  /console  Claims feed · Evidence panel · Map (Leaflet) · Timeline · Eval   │
│  /beacon   Threat banner · Nearby verified items · Rumour cards · Alarm     │
└───────────────▲───────────── REST (JSON) + SSE (/stream) ──────────────────┘
                │
┌───────────────┴──────────── Backend (FastAPI, Python 3.12) ───────────────┐
│ api/        claims · alerts · map · beacon · eval · admin(replay)          │
│ agent/      triage→cluster→extract→geocode→route→retrieve→checks→decide→explain│
│ ml/         nli · embed · llm(ollama) · vision · phash · lang               │
│ connectors/ ndma_cap · gdacs · usgs · openmeteo · nominatim · google_news · │
│             youtube_rss · gdelt · mastodon · social_replay (+ tipline API)  │
│ workers/    APScheduler ingest · watcher(re-verify) · beacon(threat)        │
│ geo/        gazetteer · polygons(shapely)                                   │
└───────────────┬─────────────────────────────────────┬──────────────────────┘
                ▼                                     ▼
       SQLite (WAL) via SQLModel              Ollama (local LLM, :11434)
       + numpy vector index (in-memory,       HF models on GPU (torch)
         embeddings stored as BLOBs)          data/snapshots (offline mode)
```

| Layer | Choice | Rejected alternatives (why) |
|---|---|---|
| API | **FastAPI** + Uvicorn, Pydantic v2 | Flask (no async or typed schemas); Django (heavy) |
| Realtime | **Server-Sent Events** | WebSockets (two-way not needed; SSE reconnects automatically) |
| Scheduler | **APScheduler** in-process | Celery/Redis (unneeded infrastructure) |
| DB | **SQLite (WAL) + SQLModel** | Postgres/PostGIS (setup time; shapely covers the geo needs at our scale); MongoDB (relational evidence links) |
| Vectors | **numpy cosine over stored embeddings** (< 10k rows) | Chroma/FAISS/pgvector (unneeded at this scale; one less dependency) |
| Frontend | **React + Vite + Tailwind + react-leaflet + TanStack Query** | Streamlit (weak for a live map, SSE and mobile alarm); Next.js (SSR not needed) |
| Map tiles | OpenStreetMap / CARTO light tiles; offline fallback: a cached tile set for the demo city | Google Maps (key and billing) |
| Alarm | Web Audio API tone + `navigator.vibrate` + Notification API | Push/FCM (HTTPS + service worker; stretch) |

## 13. Data model: handover schema v0.1 → v0.2 (additive migration)

The handover repo's `schema/schema.sql` (v0.1) is the **base**. v0.2 only **adds** columns and tables. No existing row or column is dropped, and each change is logged in `dataset_changelog.md` + `human_decisions.csv`. Engine: SQLite (WAL) via SQLModel; embeddings stored as BLOBs with numpy cosine search (≤ 50k rows; the planned ChromaDB isn't needed).

**Existing v0.1 tables: what is added**
```sql
-- sources (v0.1 kept) + layer
ALTER TABLE sources  ADD layer TEXT;                 -- official|sensor|local_news|national_global|social|research

-- claims (v0.1 kept) + post/story/triage/geo-precision
ALTER TABLE claims ADD channel TEXT;                 -- tipline|mastodon|replay|organiser|crisismmd
ALTER TABLE claims ADD language TEXT;
ALTER TABLE claims ADD geo_precision TEXT;           -- exact|city|region|dataset_event_region|unresolved
ALTER TABLE claims ADD geo_confidence REAL;
ALTER TABLE claims ADD event_time TEXT;              -- claimed event time (≠ published_at)
ALTER TABLE claims ADD bound_event_id TEXT;          -- event binding (§7.5)
ALTER TABLE claims ADD checkworthy INTEGER, ADD triage_reason TEXT, ADD priority REAL;
ALTER TABLE claims ADD story_id TEXT REFERENCES stories(story_id);
ALTER TABLE claims ADD media_ids TEXT;               -- JSON
ALTER TABLE claims ADD provenance TEXT;              -- dataset/file/row or generator + seed

-- evidence (v0.1 kept) + raw-vs-interpretation, provenance, validity, geometry
ALTER TABLE evidence ADD raw_evidence_text TEXT;     -- verbatim source text (never overwritten)
ALTER TABLE evidence ADD evidence_interpretation TEXT; -- our normalised reading; never replaces raw
ALTER TABLE evidence ADD kind TEXT;                  -- alert|observation|report|news|post|media
ALTER TABLE evidence ADD layer TEXT;
ALTER TABLE evidence ADD source_document_id TEXT;    -- e.g. CAP identifier, USGS id, AFOS product id
ALTER TABLE evidence ADD retrieval_method TEXT;      -- api|rss|archive|manual|synthetic
ALTER TABLE evidence ADD evidence_hash TEXT;         -- sha256(raw_evidence_text)
ALTER TABLE evidence ADD license_notes TEXT;
ALTER TABLE evidence ADD provenance_status TEXT;     -- VALIDATED|PROVISIONAL|SYNTHETIC|REJECTED
ALTER TABLE evidence ADD valid_from TEXT, ADD valid_until TEXT;
ALTER TABLE evidence ADD superseded_by TEXT REFERENCES evidence(evidence_id);
ALTER TABLE evidence ADD msg_type TEXT;              -- CAP Alert|Update|Cancel
ALTER TABLE evidence ADD severity TEXT, ADD urgency TEXT, ADD certainty TEXT;
ALTER TABLE evidence ADD polygon_geojson TEXT, ADD bbox TEXT;
ALTER TABLE evidence ADD quantities TEXT;            -- JSON e.g. [{"type":"magnitude","value":7.1}]
ALTER TABLE evidence ADD copy_group_id TEXT, ADD is_group_origin INTEGER;
ALTER TABLE evidence ADD embedding BLOB;

-- claim_evidence_links (v0.1 kept) + proposition-level
ALTER TABLE claim_evidence_links ADD proposition_id TEXT REFERENCES propositions(proposition_id);
ALTER TABLE claim_evidence_links ADD temporal_relation TEXT; -- before|contemporary|after|superseding|stale
ALTER TABLE claim_evidence_links ADD p_ent REAL, ADD p_con REAL, ADD weight REAL, ADD excerpt TEXT;
-- (v0.1 CHECK on relationship: SUPPORTS|CONTRADICTS|IRRELEVANT|INSUFFICIENT is kept)

-- ground_truth (v0.1 kept) + handover benchmark fields
ALTER TABLE ground_truth ADD verification_context TEXT;   -- HISTORICAL|CURRENT
ALTER TABLE ground_truth ADD verification_subtype TEXT;
ALTER TABLE ground_truth ADD atomic_propositions TEXT;    -- JSON with expected proposition states
ALTER TABLE ground_truth ADD supporting_evidence TEXT, ADD contradicting_evidence TEXT; -- JSON evidence_ids
ALTER TABLE ground_truth ADD temporal_analysis TEXT, ADD geographic_analysis TEXT, ADD uncertainty TEXT;
ALTER TABLE ground_truth ADD is_synthetic INTEGER, ADD provenance TEXT;
ALTER TABLE ground_truth ADD review_decision TEXT;        -- APPROVE|EDIT|REJECT
-- v0.1 freshness_threshold_hours is DEPRECATED (contradicts the validity-window method); kept, not used.
-- v0.1 UNIQUE(claim_id) is relaxed in practice by keying cases as (claim_id, verification_context):
-- new rows use gt_id = '<claim_id>:<context>' and a separate table avoids the UNIQUE constraint ↓
```

**New tables**
```sql
propositions(proposition_id PK, claim_id FK, idx, text, type, materiality[core|detail],
             factuality[FACTUAL|SUBJECTIVE|NON_FACTUAL], span_start, span_end, created_at)

ground_truth_cases(case_id PK, claim_id FK, verification_context, expected_status, verification_subtype,
             atomic_propositions JSON, supporting_evidence JSON, contradicting_evidence JSON,
             temporal_analysis JSON, geographic_analysis JSON, uncertainty JSON, reasoning,
             is_synthetic, provenance, review_decision, reviewer, reviewed_at, UNIQUE(claim_id, verification_context))
             -- needed because one claim can have 2 contexts (pilot 003/005); v0.1 ground_truth is UNIQUE(claim_id)

stories(story_id PK, hazard, rep_claim_id, place_text, lat, lon, first_seen_at, last_seen_at,
        post_count, languages JSON, priority, spread_30m, current_verdict_id)

verdicts(verdict_id PK, claim_id FK, story_id FK, version, verification_context, status, subtype,
         confidence, support, contra, proposition_states JSON, uncertainty JSON, explanation,
         trace_json, created_at)

observations(id PK, source_id FK, kind[precip_mm|wind_kmh|temp_c|quake_mag], lat, lon, start_at, end_at,
             value, unit, is_forecast, raw_json, fetched_at)        -- sensor layer (Open-Meteo, USGS)

subscriptions(id PK, label, lat, lon, radius_km, created_at)        -- Beacon (rounded coords)
notifications(id PK, subscription_id FK, level, title, body, story_id, evidence_id, created_at, acked_at)
media(id PK, path, kind, phash, dhash, keyframe_hashes JSON, clip_labels JSON, first_seen_at, first_seen_source)
api_cache(url_hash PK, url, fetched_at, status, body BLOB)
eval_runs(id PK, created_at, split, metrics JSON, confusion JSON, failures JSON, config JSON)
```

**Data fixes in the migration (logged as decisions):**
1. **Quarantine bad geocodes.** For "Texas/Louisiana, USA", "Caribbean/Florida, USA" and "Iran/Iraq border region":
   - set `geo_precision='dataset_event_region'` and `geo_confidence=0.2`;
   - keep the old lat/lon only in `provenance`;
   - the map draws these as region shading, never as exact pins.
2. Convert GDACS `published_at` from RFC-822 to ISO-8601 UTC.
3. Fill `raw_evidence_text` from existing `evidence_text` and compute `evidence_hash`.
4. Repair mojibake text where it can be reversed; otherwise flag it.
5. Set `provenance_status`:
   - GDACS/USGS/NWS → VALIDATED;
   - Iran casualty figures → PROVISIONAL;
   - synthetic → SYNTHETIC.

Indexes (added): `evidence(layer, event_type, valid_until)`, `evidence(copy_group_id)`, `claims(story_id)`, `stories(priority)`, `propositions(claim_id)`, `verdicts(claim_id, verification_context, version)`.

## 14. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/tipline` | Forwarded post: `{text, link?, posted_at?, lang?, lat?, lon?, media?}` → triage → story → verdict (synchronous; always checked) |
| POST | `/api/claims/check` | Same pipeline, without storing the post. Body adds `verification_context` (HISTORICAL/CURRENT, default CURRENT) and optional `claim_time`, `source_metadata` |

**Verification response (per claim; same shape as the handover's §24 contract):**
```json
{ "claim_id": "...", "claim_text": "...",
  "status": "CONFLICTING", "verification_context": "HISTORICAL", "verification_subtype": "POSITIVE_CONTRADICTION",
  "confidence": 0.71,
  "atomic_propositions": [{"id":"p1","text":"...","type":"event","materiality":"core","factuality":"FACTUAL","state":"CONTRADICTED","evidence_ids":["ev_..."]}],
  "supporting_evidence":   [{"evidence_id":"ev_...","source":"USGS","credibility_tier":"A","published_at":"...","retrieved_at":"...","location":"...","excerpt":"verbatim raw text","url":"...","temporal_relation":"contemporary"}],
  "contradicting_evidence": [],
  "temporal_analysis": {"claim_time":"...","event_time":"...","verification_time":"...","bound_event":"us2000ar20","superseded_by":null},
  "geographic_analysis": {"claim_location":"...","resolved":{"lat":0,"lon":0,"precision":"city"},"event_location":"...","distance_km":236},
  "uncertainty": ["casualty figure unverified (no positive evidence either way)"],
  "explanation": "template text citing evidence IDs",
  "trace_id": "..." }
```
| GET | `/api/stories?status=&hazard=&bbox=&since=&sort=priority` | Story feed (one row per story; post count, languages, spread) |
| GET | `/api/stories/{id}` | Story + member posts + verdict history + evidence by layer |
| GET | `/api/news?bbox=&since=&layer=` | Ingested news items (local / national / global) |
| GET | `/api/claims?status=&hazard=&bbox=&since=` | Claim-level feed |
| GET | `/api/claims/{id}` | Claim + evidence + verdict history + trace |
| GET | `/api/alerts?active=true&bbox=` | Official alerts (with polygons) |
| GET | `/api/map?bbox=&since=` | GeoJSON FeatureCollection: claims, alerts, quakes |
| GET | `/api/stream` | SSE: `story.new`, `story.verdict`, `story.status_changed`, `alert.new`, `news.new`, `beacon.level` |
| POST | `/api/beacon/subscribe` | `{lat, lon, radius_km}` → subscription id |
| GET | `/api/beacon/{sub_id}/status` | Threat level + reasons + nearby verified items + rumour cards |
| POST | `/api/beacon/{sub_id}/ack/{notification_id}` | Acknowledge |
| POST | `/api/admin/replay` | `{scenario, speed}` start the scenario replay clock (demo) |
| POST | `/api/admin/ingest-now` | Force a connector poll |
| GET | `/api/eval/latest` · POST `/api/eval/run` | Evaluation metrics |
| GET | `/api/health` | Models loaded, connectors OK, snapshot mode |

## 15. Folder structure

```
Hacknova/                         ← handover repo copied in WITHOUT .venv (it becomes the base)
├── schema/schema.sql             v0.1 (handover) + migrations/0002_v02.sql (§13)
├── dataset/                      (handover) raw/ · processed/ · synthetic/ · ground_truth/ · benchmark/eval_set.jsonl · reports/
├── dataset_workflow_state.json · dataset_changelog.md · human_decisions.csv   (handover; kept up to date)
├── docs/
│   ├── PRD.md                    ← this file
│   ├── ARCHITECTURE.md           ← technical explanation deliverable
│   └── EVAL.md                   ← metrics, confusion matrix, ablations
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI app, CORS, startup (load models, scheduler)
│   │   ├── config.py             thresholds, τ/R/W per hazard, credibility table, SNAPSHOT_MODE
│   │   ├── db.py · models.py     SQLModel engine + tables (§13)
│   │   ├── schemas.py            Pydantic I/O models
│   │   ├── api/                  claims.py · alerts.py · map.py · stream.py · beacon.py · eval.py · admin.py
│   │   ├── agent/
│   │   │   ├── graph.py          state-graph runner (async, traced)
│   │   │   ├── state.py          VerificationState dataclass
│   │   │   ├── tools.py          typed tool functions (cached, timeouts)
│   │   │   ├── policies.py       hazard routing, decision table, thresholds
│   │   │   └── nodes/            triage · cluster · extract · decompose · geocode · bind_event · route · retrieve · stance · numeric · freshness · timing · media · decide · explain
│   │   ├── ml/                   nli.py · embed.py · llm.py (ollama) · vision.py (clip) · phash.py · lang.py
│   │   ├── connectors/           base.py (cache+snapshot+rate limit) · ndma_cap.py · gdacs.py · usgs.py · openmeteo.py · nominatim.py
│   │   │                         google_news.py · youtube_rss.py · gdelt.py · mastodon.py · social_replay.py
│   │   ├── news/                 copygroup.py (copied-source rule) · layers.py (local/national/global classification)
│   │   ├── geo/                  gazetteer.py · polygons.py
│   │   ├── beacon/               threat.py · notifier.py
│   │   └── workers/              scheduler.py · watcher.py · events.py (in-process pub/sub → SSE)
│   ├── tests/                    test_decide.py · test_freshness.py · test_geo.py · test_extract.py · test_api.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                Console.jsx · ClaimDetail.jsx · Beacon.jsx · Eval.jsx
│   │   ├── components/           ClaimCard · StatusBadge · EvidencePanel · MapView · Timeline · CheckBox · ThreatBanner · RumourCard · ReplayControls
│   │   ├── lib/                  api.js · sse.js · alarm.js (Web Audio + vibrate + Notification)
│   │   └── main.jsx · App.jsx
│   └── package.json
├── config/
│   ├── channels.yaml             news channels: id, name, layer (local/national), language, region
│   ├── hazards.yaml              multilingual hazard + severity lexicon (en/hi/mr/te)
│   └── settings.yaml             thresholds, τ/R/W per hazard, layer trust, poll intervals
├── data/
│   ├── synthetic/                posts.jsonl · news.jsonl · alerts_sim.jsonl · reports.jsonl · labels.csv
│   ├── snapshots/                ndma/*.xml · gdacs/*.xml · usgs/*.json · openmeteo/*.json · news/*.xml · youtube/*.xml (captured on event day)
│   ├── gazetteer/                IN.txt (GeoNames) → india_places.parquet
│   ├── media/                    images/ · videos/ · archive_index.json (first-seen dates)
│   └── db/evidence.db            (handover DB, migrated to v0.2; single DB for app + dataset)
├── scripts/                      handover: load_sources · download_gdacs · download_reliefweb · normalize_* · geocode_locations · validate_dataset · build_benchmark · evaluate_system
│   ├── migrate_v02.py            additive schema migration + geocode quarantine + ISO dates + hashes
│   ├── fetch_primary_evidence.py USGS FDSN · IEM AFOS (NWS) · ReliefWeb · NDMA CAP → evidence rows with provenance
│   ├── propose_candidates.py     candidate claims + decomposition + link proposals (Gemini/local), never auto-approved
│   ├── review_cases.py           local APPROVE / EDIT / REJECT review page → ground_truth_cases + human_decisions.csv
│   ├── download_models.py        pre-fetch HF models + `ollama pull qwen2.5:3b-instruct`
│   ├── snapshot_feeds.py         save live feeds for offline demo
│   ├── build_gazetteer.py
│   ├── make_synthetic.py         scenario generator with labels (§11)
│   ├── seed_db.py
│   └── run_eval.py               dev/test metrics → eval_runs + docs/EVAL.md
├── presentation/                 final deck (official template) + screenshots
├── HACKNOVA_PROBLEM_ANALYSIS.md · PS2_PS5_BUILD_PLANS.md
└── README.md                     run instructions (one command each for backend/frontend)
```
*(The earlier `energyiq/` PS-1 draft is kept but unused; it can be deleted on request.)*

## 16. UI specification

- **Console:**
  - Left: **story feed** sorted by priority. Each row shows status badge, hazard icon, "N posts · hi/mr/en", spread sparkline and confidence. Non-claims are hidden behind a "filtered out (N)" toggle.
  - Centre: Leaflet map (CAP polygons shaded by severity; claims as coloured pins: 🟢 verified, 🟠 conflicting, ⚪ outdated, 🔵 unverified; quake circles sized by magnitude).
  - Right: evidence panel with "For" / "Against" columns, **grouped by layer** (Official · Sensors · Local news · National/global · Other posts). Each item shows source, timestamp + age, distance / "inside alert area", NLI bar, link, and "also reported by N outlets (copies)". Above the columns sits a mini timeline: when the posts appeared vs when local, national and official sources reported.
  - Top: "Check a post" box + replay controls.
  - Bottom: verdict timeline.
- **Beacon (mobile-first):**
  - Full-width threat banner with colour and a large icon.
  - "Why" line with the evidence source and expiry.
  - Nearby verified items.
  - Rumour-check cards.
  - Alarm (3 rising tones + vibrate) on escalation to RED; "I'm safe / Acknowledge" button.
  - Location picker fallback (city search).
- **Eval page:** confusion matrix, per-class precision/recall/F1, ablations, latency.

## 17. Evaluation plan

1. **Verdict quality:** macro-F1, per-class P/R, and a confusion matrix on the **test split**.
2. **Ablations:** −freshness, −geo, −numeric, −NLI (rules only), and translated-English-only vs multilingual. Shows each component's contribution.
3. **Extraction accuracy:** field-level exact or near-match on 50 hand-checked posts.
4. **Triage:** precision and recall of "worth checking" vs `not_a_claim` labels (target ≥ 0.85 / ≥ 0.90; missing a real claim is worse than checking a prayer).
5. **Story grouping:** pairwise precision and recall vs `label_story`; posts per story.
6. **Layer ablation:** −local news, −sensors, −official, and "count copies as independent" vs the copied-source rule. Shows why each layer and the independence rule matter.
7. **Safety metrics:** false-VERIFIED rate; Beacon false alarms in replay.
8. **Latency:** p50/p95 per claim; verifications saved by grouping (posts ÷ stories).
9. **Per-context results:** HISTORICAL and CURRENT reported separately; proposition-level accuracy for material propositions.
10. **Failure categories (adopted from the handover):** each wrong case is tagged automatically from its trace as one of: *retrieval failure* (the right evidence was never retrieved), *grounding failure*, *event-binding failure*, *temporal failure*, *geographic failure*, *contradiction failure*, *uncertainty failure*.
11. **Critical errors (reported separately, target 0):** UNVERIFIED→CONFLICTING (treating absence as contradiction), OUTDATED→CONFLICTING (confusing superseded with false), HISTORICAL VERIFIED→CONFLICTING.

The handover's `evaluate_system.py` becomes the runner: it calls `POST /api/claims/check` with `verification_context`, writes `dataset/reports/evaluation_report.md` + `failure_analysis.md`, and stores an `eval_runs` row.

All numbers are generated by `scripts/run_eval.py` and shown on the slides exactly as measured.

## 18. Non-functional requirements

- **Offline-capable:** `SNAPSHOT_MODE=1` serves all connectors from `data/snapshots`; models are pre-downloaded.
- **Performance:** models load once at startup; NLI is batched; API responses are cached.
- **Privacy:** post author handles are hashed; no personal data is stored; Beacon location stays in the browser and the subscription stores only rounded coordinates (0.01°).
- **Security:** admin endpoints are restricted to localhost; input length limits; no execution of fetched content.
- **Responsible AI:**
  - The app never labels a claim *false* on absence of evidence.
  - Every verdict is traceable.
  - The Beacon alarm is triggered only by official or verified evidence.
  - Synthetic data is labelled everywhere in the UI.

## 19. Execution timeline (8.5 h, roles for a team of 4)

| Time | A — Backend / feeds | B — ML / agent | C — Frontend | D — Data / eval / deck |
|---|---|---|---|---|
| 0:00–0:30 | Copy the handover repo (no `.venv`), run `migrate_v02.py`, FastAPI skeleton | Test the Gemini key; download models + Ollama pull | Vite + Tailwind + Leaflet skeleton | `fetch_primary_evidence.py` for the 5 pilots; snapshot live feeds |
| 0:30–2:30 | Connectors (NDMA CAP + polygons, GDACS, USGS, Open-Meteo, **Google News, YouTube RSS**), cache, snapshot mode, copied-source rule | **triage + cluster**, extract, geocode, retrieve, stance, numeric, freshness, **timing** nodes | Console layout, story feed, map with alerts | `make_synthetic.py` scenarios + news + labels; `channels.yaml` + `hazards.yaml` lexicon |
| 2:30–4:30 | API endpoints (tipline, stories), SSE, replay admin | decide + explain + graph runner; tests | Evidence panel by layer, filters, timeline, tipline box | `propose_candidates.py` → **human review gate** (~50 cases) → `eval_set.jsonl`; threshold tuning on dev |
| **4:30–5:00** | **Integration gate: Phase 1 demo flow runs end-to-end** | | | |
| 5:00–6:30 | Watcher re-verification, Beacon threat API | Media pHash + CLIP (P3) | Beacon page + alarm + rumour cards | Eval on test, ablations, ARCHITECTURE.md |
| 6:30–7:30 | Bug fixes, health endpoint | Latency tuning | Polish, mobile layout | Screenshots, deck draft |
| 7:30–8:30 | Demo rehearsal in offline mode; final fixes; deck complete | | | |

**Cut order if behind:** media check (P3) → GDELT + Mastodon connectors → LLM rephrasing → watcher auto re-verify (keep a manual "re-check") → Beacon notifications (keep the banner and alarm). **Never cut:** triage, story grouping, the copied-source rule, Google News local search (they answer "which posts" and "local vs global").

## 20. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NLI misreads short or slangy posts | M | H | Numeric, geo and time rules dominate where applicable; abstain to UNVERIFIED when the signals disagree |
| Local LLM slow or broken | M | M | LLM is optional: rules-only extraction + template explanations |
| Live feeds down at the venue | M | H | Snapshot mode, captured beforehand |
| Ambiguous place names | H | M | Context-based disambiguation + `geo_ambiguous` flag + user confirmation |
| Organisers' synthetic data format differs | M | M | Loader with column mapping; regenerate our scenarios |
| Judges question synthetic data | M | M | Real NDMA/GDACS/USGS evidence + CrisisMMD-derived text; synthetic clearly labelled; ground truth explained |
| Alarm blocked by browser autoplay | H | M | "Enable alerts" tap on first load unlocks audio and notification permission |
| VRAM contention | L | M | Lazy-load CLIP; use the 3B LLM |
| "You don't actually monitor social media" | H | M | Lead with the tipline model (how real fact-checking works); show Mastodon live; explain why X/WhatsApp are not accessible |
| Google News RSS throttles or changes format | M | M | Cache per query (10 min); snapshot news for demo scenarios; YouTube RSS and GDELT as backups |
| Local news is early but wrong | M | M | Lower trust than official and sensor layers; a single layer gets no bonus; contradictions shown side by side, not hidden |
| Copied stories inflate confidence | H | H | Copied-source rule (cosine ≥ 0.9 / same byline → earliest publisher only) + layer-diversity requirement |
| Story grouping merges two different events | M | M | Require same hazard + ≤ 25 km + ≤ 24 h as well as text similarity; responder can split a story in the Console |

## 21. Demo script (about 4 minutes)

*Counts in the script (60 posts, 4 stories, 142 mm, 23 times) are scenario design targets for the replay data, not measured results. Eval numbers are shown exactly as `run_eval.py` reports them.*

1. **Console, live mode:** real NDMA alerts appear on the map with polygons (shows real data).
2. **Replay scenario S1 (Pune flood):** 60 posts stream in. Triage filters out 15 prayers and appeals, and the rest group into 4 stories ("4 verifications instead of 45").
   - "Heavy flooding on Sinhagad Road" → **VERIFIED**: inside the CAP polygon, Open-Meteo shows 142 mm, and a Marathi local news report from 40 minutes ago matches. Three independent layers agree; the evidence timeline shows local news before national.
   - "300 mm rain, Khadakwasla dam burst" → **CONFLICTING** (measured 142 mm; no dam alert; NLI contradiction).
3. **Hindi post** about a flood in Pune → matched to the English NDMA alert → VERIFIED (multilingual).
4. **Recycled Kolhapur 2019 video** → **OUTDATED** (media first seen in 2019; no current alert).
5. **Delhi "M6.8" rumour** → contradicted by USGS M3.1.
6. **Tipline:** paste a forwarded WhatsApp-style message live. It joins an existing story and gets that story's verdict instantly, with "seen 23 times in 3 languages".
7. **Beacon on a phone-sized view (Pune):** the alarm sounds for the official, verified flood alert. A rumour card says "dam burst: not confirmed".
8. **Eval page:** macro-F1, confusion matrix and ablations (as measured).

## 22. Open questions
1. Final team size and roles. The timeline assumes 4 people.
2. Will the organisers release their synthetic posts and alerts at the start? If so, add a loader in the first hour.
3. Is internet access at the venue reliable? This decides live mode vs snapshot mode for the demo.
4. Do we request a ReliefWeb app name now? It costs nothing; approval time is unknown.
5. Which regional news channels go in `channels.yaml`? Proposed: Lokmat, ABP Majha, TV9 Marathi, Pudhari (Marathi); Aaj Tak, ABP News (Hindi); NDTV, DD News (national). Channel IDs still need to be looked up and each feed checked.
6. Should a Reddit OAuth app be registered (free) to add a second open social source?
7. **May we test the handover's Gemini key and ReliefWeb app name with one small request each?** This decides the LLM primary/fallback order and whether ReliefWeb is live or cached.
8. Who on the team is the **human reviewer** for the benchmark gate? About 50 approvals at roughly 1 minute each.
