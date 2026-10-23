# PS-2 vs PS-5 — Deep Dive and Build Plans

Source checks were run live on 23 Oct 2026 from this laptop. ✅ = works · ⚠️ = works with limits · ❌ = blocked.

## 0. What the source checks showed

| Source | Status | What it means for us |
|---|---|---|
| **NDMA SACHET CAP feed** (`sachet.ndma.gov.in/.../rss_india.xml`) | ✅ live, 83 KB, free | Official Indian alerts in real time. **Multilingual** (Hindi, Telugu, …). This is our strongest "trusted source" for PS-2. |
| **GDACS RSS** (`gdacs.org/xml/rss.xml`) | ✅ 900 KB, includes geo + alert level | Global floods, cyclones and earthquakes with coordinates. |
| GDACS JSON API | ❌ timed out from here | Use the RSS feed instead. |
| **ReliefWeb API** | ❌ v1 shut down; v2 returns 403 without an *approved* app name | Must be requested in advance. Treat it as optional; use cached reports. |
| Open-Meteo (rainfall/weather) | ✅ free, no key | Lets us check claims like "300 mm rain in Mumbai" against measured rainfall. |
| USGS earthquakes GeoJSON | ✅ free | Lets us check magnitude and location claims. |
| Nominatim geocoding | ✅ (1 request/sec policy) | Turns place names into coordinates. Cache results plus an offline district list as backup. |
| CrisisMMD | ✅ page is up (download form) | Real disaster tweets, useful for realistic test posts. |
| **Wayback CDX API** | ✅ returned dated Notion pricing snapshots | PS-5 can show **real** price history from day one. |
| Wayback "availability" API | ⚠️ rate-limited (429) | Use the CDX endpoint and cache results. |
| Live SaaS pricing pages (Notion, Linear) | ✅ fetchable; Notion's robots.txt allows `/pricing` | Real monitoring targets are possible. |
| Local hardware | ✅ **RTX 4050, 6 GB VRAM**, torch installed; transformers installable | We can run NLI models, multilingual embeddings, or a small local LLM (e.g. Qwen2.5-7B 4-bit via Ollama, about 5 GB). **No paid API key needed.** |

---

## 1. PS-2 — Disaster Information Verification Agent

### The problem in plain terms
During the 2026 monsoon, a WhatsApp forward says *"Khadakwasla dam gates opened, Sinhagad Road flooding in 2 hours, evacuate now"*. It might be:
- **true** (the official alert exists),
- **outdated** (true in 2019, now being re-forwarded),
- **conflicting** (the district office says only one gate opened and the risk is low), or
- **unverifiable**.

Responders waste time chasing false reports, and real alerts get lost in the noise. The judges want an agent that gives each claim one of four verdicts, **with evidence, timestamps, a map, and honest uncertainty**.

### What the organisers require (mandatory)
- Claim extraction
- Comparison against alerts, reports and weather
- Freshness
- Contradictions
- Geo-verification
- A 4-way status: *verified / conflicting / outdated / unverified*
- Evidence per claim
- An evidence dashboard
- An **interactive map**
- A technical explanation

The rules forbid unsupported claims and require uncertainty to be stated.

### How we'd build it — "SachVerify"

```
Posts (synthetic + CrisisMMD-style, EN/HI/MR)  ─┐
                                               ▼
1. CLAIM EXTRACTION   event type · place · time · quantity · assertion
   (spaCy NER + Indian place gazetteer + dateparser; local LLM optional, output checked against the source text)
                                               ▼
2. EVIDENCE RETRIEVAL  candidates filtered by:  same hazard type  ∧  within R km  ∧  time window
   Sources: NDMA CAP (live + snapshot), GDACS RSS, Open-Meteo rain, USGS quakes, synthetic incident reports
   Ranked by multilingual embeddings (e5-small) → a Hindi post can match an English alert
                                               ▼
3. CHECKS (each produces a signal with its own explanation)
   • Stance: NLI model (DeBERTa-MNLI / multilingual XNLI) → supports / contradicts / neutral
   • Numbers: "200 mm rain" vs Open-Meteo measured; "M6.5" vs USGS magnitude
   • Geo: distance from the claimed place to the alert area or epicentre
   • Freshness: evidence age, CAP 'expires', Update/Cancel messages → superseded alerts
   • Source credibility: official > news > NGO > anonymous social
                                               ▼
4. VERDICT ENGINE (transparent rules, not a black box)
   Verified    = fresh, credible, supporting evidence AND no fresh credible contradiction
   Conflicting = credible support AND credible contradiction
   Outdated    = only expired or superseded evidence matches, or the event date is far before the post date
   Unverified  = nothing credible within the geo/time window → "insufficient evidence", never a guess
   + a confidence score and a one-line plain-language reason
                                               ▼
5. DASHBOARD   claim feed with status badges · evidence for/against (source, timestamp, link) ·
               Leaflet map (claims coloured by status + alert areas) · timeline · filter by district
```

### What makes it stand out
1. **Multilingual verification.** A Hindi or Marathi rumour is checked against an English NDMA alert. This fits India and few teams will do it.
2. **Detects recirculated old news.** It flags true-but-old claims as *outdated*. This is the most common real-world misinformation pattern.
3. **Live official feed.** Real NDMA alerts appear during the demo, with a cached snapshot as a fallback.
4. **Measured accuracy.** We build a labelled test set of about 150 posts across the 4 statuses and report macro-F1 and a confusion matrix, plus an ablation showing that removing the freshness check turns "outdated" into "verified".

### Effort (8–9 h, 3–4 people)
| Block | Hours |
|---|---|
| Synthetic posts + alerts + labels (realistic, EN/HI, with ground truth) | 1.5 |
| Feed adapters (NDMA CAP, GDACS RSS, Open-Meteo, USGS) + cache | 1.5 |
| Claim extraction + geocoding | 1.5 |
| Retrieval + NLI + numeric/geo/freshness checks + verdict engine | 2 |
| Dashboard + map | 2 |
| Evaluation + demo + slides | 1.5 |

### Risks and mitigations
| Risk | Mitigation |
|---|---|
| NLI is weak on short, slangy posts | Combine it with numeric/geo/time rules; label the result "Unverified" when the signals disagree |
| Ambiguous place names ("Shivaji Nagar" exists in many cities) | District context + gazetteer + ask the user to confirm |
| Live feeds change or go down | Snapshot cache; the demo runs fully offline |
| Organisers' synthetic data format unknown | Loader adapter with column mapping |
| Model download time | Pre-download models before the event starts |

**Verdict:** the highest judge appeal and real social impact. Medium risk. Feasible now that local models run on the GPU.

---

## 2. PS-5 — Competitor Intelligence and Market Monitoring Agent

### The problem in plain terms
A startup product manager tracks 5 competitors. Notion quietly raises its Plus plan price, Linear adds AI features to its free tier, and ClickUp repositions as an "AI workspace". The PM learns about this weeks later from a customer. A naive page-diff tool raises 40 alerts a day for rotating testimonials and cookie banners, so people ignore it. The judges want **meaningful-change detection, dated history, configurable comparison, and reports in which every claim links to its source and observation date**. The **required demo** is: monitor pages, introduce a simulated price or feature change, generate a sourced report.

### How we'd build it — "RivalRadar"

```
Config (YAML/UI): competitors × URLs (pricing, features, changelog/blog RSS) × criteria
                                               ▼
1. COLLECT   requests / Playwright (JS pages) · robots.txt check · rate limit · scheduler
             → raw snapshot + timestamp + hash (SQLite + files)
   BACKFILL  Wayback CDX → real dated history (e.g. Notion pricing 2023→2026) on day one
   MOCK      local "competitor" site we control → the official simulated-change demo
                                               ▼
2. NORMALISE   strip scripts, nav, cookie banners, dates, counters, A/B ids → stable content blocks
                                               ▼
3. EXTRACT   structured fields: plans[], price, currency, billing period, seat limits, features[], headline/tagline
             (DOM + regex rules first; local LLM fallback with a "value must appear verbatim in the page" check)
                                               ▼
4. CHANGE DETECTION (structured diff, not an HTML diff)
   • price change old→new, Δ%           • plan added/removed
   • feature added/removed (fuzzy match) • positioning: headline embedding shift
   • cosmetic/noise → suppressed and logged
   Significance = category weight × magnitude × competitor priority × user watch rules
                                               ▼
5. OUTPUTS   timeline per competitor · comparison matrix (each cell: value + source + date) ·
             alerts (in-app + optional Telegram/Slack/email webhook) · report (MD/PDF, every claim footnoted)
```

### What makes it stand out
1. **Real history on day one.** Wayback backfill shows real dated price changes, not only synthetic ones.
2. **Measured noise suppression.** We report "raw diff would have raised N alerts; we raised M, with X% precision" on a labelled set of cosmetic vs meaningful changes.
3. **Evidence-locked reports.** Every number in a report is checked to appear verbatim in the stored snapshot, with the URL, timestamp and snapshot link.
4. **Configurable criteria matrix.** The user defines attributes (e.g. "entry price/seat", "SSO on which plan", "free-tier limit") and the matrix fills itself with sources.

### Effort (8–9 h)
| Block | Hours |
|---|---|
| Mock competitor site + config + SQLite schema | 1 |
| Fetcher + robots check + snapshot store + Wayback backfill | 1.5 |
| Normaliser + structured extractor (3–4 real pages + mock) | 2 |
| Diff + significance + noise filter | 1.5 |
| Dashboard (timeline, matrix, alerts) + report export | 2 |
| Labelled change set + evaluation + demo + slides | 1 |

### Risks and mitigations
| Risk | Mitigation |
|---|---|
| Real pages are JS-heavy or anti-bot | Playwright; per-site selectors; mock site always works |
| Website terms of service | Only robots-allowed pricing/changelog pages, low frequency, cited |
| Page layouts break the extractor | Per-site selector config + LLM fallback with verbatim check |
| "Just a scraper" perception | Lead the pitch with significance scoring + measured noise suppression + evidence locking |

**Verdict:** the most deterministic and reliable demo, with judging criteria that are all mechanical and achievable. Lower "wow" than PS-2, and more teams may build similar dashboards.

---

## 3. Head-to-head

| | PS-2 SachVerify | PS-5 RivalRadar |
|---|---|---|
| Judge "wow" / social impact | **High** (disasters, India, multilingual, map) | Medium (business tool) |
| Core technical risk | NLI and claim-extraction quality | Extraction from varied page layouts |
| Data in hand today | Live NDMA + GDACS + weather; we create labelled posts | Live pages + Wayback history + our mock site |
| Demo reliability | Good with snapshot fallback | **Very high** (we control the mock site) |
| Accuracy can be proven | Yes (labelled posts → macro-F1) | Yes (labelled changes → precision/recall) |
| Differentiation vs other teams | **Strong** (multilingual + recirculated news + live official feed) | Moderate (noise suppression + evidence lock) |
| Needs AI model | Yes (local NLI/embeddings on the RTX 4050) | Optional |
| Updated weighted score* | **76.0** | 68.5 |

*Re-scored with the GPU finding: PS-2 feasibility 5→7 and data 4→7; PS-5 data 6→8 and demo 7→8. PS-1 is still 84.0 on the same rubric. Its lead comes from feasibility and data certainty, not impact or originality.

**Recommendation: PS-2**, *if* someone on the team is comfortable with Python NLP and the models are downloaded before the clock starts. Choose **PS-5** if the team prefers a lower-risk build that will certainly work, or if the frontend/scraping skills are stronger than the NLP skills.
