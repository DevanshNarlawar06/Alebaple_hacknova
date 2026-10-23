# SachVerify — UI prompts for Google Stitch (desktop + phone)

**How to use:**
1. Paste **Prompt 0 (design system)** first in every Stitch project, or at the top of each screen prompt.
2. Generate one screen per prompt. Stitch does better with one screen at a time.
3. Desktop prompts use **Web, 1440 px**. Phone prompts use **Mobile, 390 px**.
4. Keep the same design system so both apps look like one product.

All names, places and numbers below are **sample content** for the mock-ups. In the real app they come from the API.

---

## Prompt 0 — Design system (paste first)

```
Design system for "SachVerify", a calm, trustworthy disaster-information verification product.
Style: minimalist, editorial, lots of white space, quiet and factual, like a well-designed
government data tool crossed with Linear / Notion. No gradients, no glassmorphism, no stock
illustrations, no emojis in the UI, no heavy shadows (only 1px borders and very soft elevation).

COLOUR — neutral first, colour only to carry meaning. Red is used extremely sparingly.
- Background: #FAFAF9 (warm off-white). Surfaces/cards: #FFFFFF. Borders: #E7E5E4.
- Text: primary #1C1917, secondary #57534E, muted #A8A29E.
- Brand accent: deep teal #0F766E (buttons, links, focus rings, selected states).
- Status colours (muted, used as small pills/dots with tinted backgrounds, never large fills):
  VERIFIED     teal-green  #15803D on #F0FDF4
  CONFLICTING  amber       #B45309 on #FFFBEB
  OUTDATED     slate       #475569 on #F1F5F9
  UNVERIFIED   indigo-blue #4338CA on #EEF2FF
- Beacon threat levels: ALL CLEAR = teal-green, WATCH = amber.
  ALERT = muted coral #C2410C, used ONLY for the active-alert banner on the phone app.
  Never use bright red (#FF0000-like) anywhere. No red buttons, no red text paragraphs.
- Map: light grey basemap (CARTO Positron style). Alert areas drawn as thin outlines with 8% fill.

TYPOGRAPHY
- Inter (or Geist). Headings semibold, body regular. Sizes: 28/20/16/14/12.
- Numbers, timestamps and IDs in tabular figures / JetBrains Mono at 12–13px.
- Sentence case everywhere, no ALL CAPS except tiny 11px labels with letter-spacing.

COMPONENTS
- Status pill: small rounded-full pill, dot + label (e.g. "● Verified"), tinted background.
- Confidence: thin 4px bar with "High / Medium / Low" text, never a big gauge.
- Evidence item: source name + small source-type tag (Official / Sensor / Local news /
  National / Post), timestamp with relative age ("2 h ago"), location line, a 2-line verbatim
  excerpt in a quote style, "Open source ↗" link.
- Proposition row: short sentence, tiny tag (core/detail, factual/subjective), state icon
  (✓ supported, ✕ contradicted, ? unverified, ⟲ superseded) in the status colours.
- Cards: 12px radius, 1px border, 16–24px padding. Icons: Lucide, 1.5px stroke, 18px.
- Empty and uncertain states are first-class: show "Not enough evidence yet" calmly, never as an error.
Tone of copy: plain, precise, non-alarming. Say "Not confirmed" instead of "FAKE".
```

---

## DESKTOP — Responder Console (web, 1440 px)

### D1 — Console home: stories + map + evidence (the main screen)
```
Using the SachVerify design system, design the main desktop screen "Console" for emergency
responders, 1440px wide, three columns.

Top bar (56px): small wordmark "SachVerify" left; centre a search field "Search place, hazard or
claim"; right: a segmented control "Live | Replay", a small grey dot "Live feeds OK", a teal
button "Check a post", avatar.

Left column (360px) — "Stories" feed sorted by priority:
- Filter row: chips "All · Verified · Conflicting · Outdated · Unverified", hazard dropdown,
  time dropdown "Last 24 h", and a quiet link "Filtered out (15)".
- 6 story cards, each: hazard icon, one-line representative claim, place + relative time,
  status pill, "23 posts · hi · mr · en", tiny sparkline of spread, confidence bar.
  Example cards:
  1) "Sinhagad Road under 3–4 ft water" — Pune · 18 min ago — Verified — High
  2) "Khadakwasla dam gates burst, evacuate now" — Pune · 25 min ago — Conflicting — High
  3) "Old video: Kolhapur bridge washed away" — Kolhapur · 40 min ago — Outdated — High
  4) "Lightning deaths reported in Anantapur" — Andhra Pradesh · 1 h ago — Unverified — Low
  5) "M6.8 earthquake in Delhi, buildings collapsed" — Delhi · 2 h ago — Conflicting — High
  6) "Shelters open at Fergusson College" — Pune · 2 h ago — Verified — Medium
  Card 2 is selected (teal left border).

Centre column (flexible) — Map:
- Light basemap of Maharashtra/Pune. One official alert area outlined in thin coral-grey
  with 8% fill labelled "NDMA · Flood · until 17:30".
- Claim pins as small coloured dots by status, clustered with counts.
- Map legend bottom-left (tiny, 4 statuses + "Official alert area").
- Top-right map controls: layers toggle (Official alerts, Claims, Sensors, News), zoom.

Right column (420px) — Story detail for the selected story:
- Claim text large, status pill "Conflicting", subtype tag "Numeric conflict", confidence Medium-High.
- Context toggle "Current | Historical".
- "What's being claimed" — 3 proposition rows:
   ✓ "Heavy rain and flooding in Pune today" (core, supported)
   ✕ "Khadakwasla dam gates burst" (core, contradicted)
   ? "Evacuate within 2 hours" (detail, unverified)
- Two-column evidence section "Supports (2)" / "Contradicts (2)" with compact evidence items:
   Supports: NDMA SACHET alert (Official, 42 min ago), Open-Meteo 142 mm in 24 h (Sensor).
   Contradicts: Pune Irrigation Dept release notice "controlled discharge 9,000 cusecs"
   (Official, 30 min ago), Lokmat local news "gates opened in controlled manner" (Local news).
- Small timeline strip: posts first seen 13:05 → local news 13:20 → official 13:35.
- Plain-language explanation (2–3 sentences) and an "Uncertainty" note in muted text.
Overall: calm, dense but breathable, nothing shouty.
```

### D2 — Claim / story detail (full page, reasoning view)
```
SachVerify design system. Desktop full-page "Story detail" for one claim, 1440px, single
centred column 880px with a sticky right rail 300px.

Header: breadcrumb "Stories / Pune", claim text as H1, status pill "Outdated",
subtype "Superseded directive", context switch "Current | Historical" where Historical shows
"Verified" — show both small pills side by side with a caption "True when posted, no longer current".
Meta row: first seen time, post count 41, languages, channels (Tipline, Replay).

Sections stacked as quiet cards:
1. "Atomic facts" — table: fact · type · core/detail · factual/subjective · state · evidence count.
   Include one subjective row ("Scariest night of my life") greyed with tag "Subjective — excluded".
2. "Evidence" — tabs by layer: Official · Sensors · Local news · National/global · Other posts.
   Each evidence row: source, credibility tier letter in a tiny square (A/B/C/D), published and
   retrieved timestamps, location + distance ("inside alert area" / "236 km away"),
   temporal relation tag (Before / Same time / After / Superseding), verbatim excerpt, link.
   Show one row tagged "Superseded by ev_7f2…" with strikethrough-free muted styling.
   A collapsed line "Also reported by 6 outlets (copies — counted once)".
3. "Time" — horizontal timeline with 4 markers: event time, claim time, evidence times,
   verification time; validity window shown as a light band that ends before "now".
4. "Place" — small static map with claim location (approximate shown as soft circle,
   label "Region-level precision") and event location.
5. "Why this status" — explanation paragraph citing evidence IDs as small chips;
   "Uncertainty" bullet list in muted text.
Right rail: verdict history (versions with time and status change), actions:
"Re-check now", "Copy summary", "Flag for review". No red anywhere on this page.
```

### D3 — Check a post (tipline) modal
```
SachVerify design system. Desktop modal (640px) "Check a post".
Fields: large textarea "Paste the message, caption or link", optional row: "Posted at" datetime,
"Place (if known)", "Language: Auto", and a dashed drop zone "Add screenshot or video (optional)".
Toggle "Verification context: Current | Historical".
Primary teal button "Verify", secondary "Cancel".
Show the result state below the form after submission: a compact result card with status pill
"Unverified", line "Flooding confirmed; the reported looting is not confirmed by any source",
"Joined existing story · seen 23 times in 3 languages", and link "Open full story →".
Also show a slim progress list while checking (muted, checkmarks appearing):
"Reading claim · Splitting into facts · Finding place · Searching official alerts ·
Checking weather · Searching local news · Deciding".
```

### D4 — Evaluation page
```
SachVerify design system. Desktop page "Evaluation", 1440px.
Top: 4 metric cards — Macro-F1, Accuracy, Critical errors (target 0), Median latency — values as
placeholders "0.00" with small caption "test split · n = 30". Muted, no colours except status dots.
Left: 4×4 confusion matrix (Verified, Conflicting, Outdated, Unverified), cells shaded in a single
teal scale, diagonal emphasised.
Right: per-status precision/recall/F1 table; below it "Failure categories" horizontal bars
(retrieval, grounding, event binding, temporal, geographic, contradiction, uncertainty).
Bottom: "Critical errors" list with three rows: Unverified→Conflicting, Outdated→Conflicting,
Historical verified→Conflicting, each with a count and "view cases" link.
Ablation table: Full system vs −freshness, −geo, −local news, −NLI.
Footer caption: "All numbers produced by run_eval.py — not hand-entered."
```

### D5 — Benchmark review gate (for the human reviewer)
```
SachVerify design system. Desktop review tool "Review case 12 of 58", 1440px, two panes.
Left pane: claim text, source + "Synthetic" or "Real (CrisisMMD)" tag, proposed context and
status, atomic facts with proposed states, proposed supporting and contradicting evidence
(each with verbatim excerpt + link), time analysis, place analysis, proposed reasoning.
Right pane: editable form — status select, subtype select, context select, per-fact state
selects, reviewer note. Bottom sticky bar with three buttons: "Reject" (quiet outline),
"Edit & approve" (outline teal), "Approve" (solid teal). Keyboard hints A / E / R.
Progress bar at top: 34 approved · 6 edited · 9 rejected · 9 left.
```

---

## PHONE — Beacon (mobile, 390 px)

### M1 — Home: all clear
```
SachVerify design system, mobile 390×844, app name "Beacon by SachVerify".
Top: location chip "Kothrud, Pune ▾" and a small settings icon.
Hero card (full width, calm teal-green tint): large check icon, "All clear near you",
caption "No verified threats within 10 km · updated 1 min ago".
Section "Nearby updates": 3 compact rows with status pill + one line + distance + time:
  ● Verified · "Heavy rain expected tonight (IMD/NDMA)" · 4 km · 20 min
  ● Outdated · "Bridge collapse video is from 2019" · 120 km · 1 h
  ● Unverified · "Water-logging at Karve Road" · 2 km · 35 min
Section "Rumour check" — one card: "Viral: 'Khadakwasla dam burst'" → "Not confirmed.
Official notice says controlled release." with link "See evidence".
Bottom: floating teal button "Check a message". Bottom nav: Home · Map · Check · Settings.
Very calm, generous spacing, no red.
```

### M2 — Home: watch state
```
Same as M1 but the hero card is amber-tinted: icon eye/alert-circle, "Watch: reports of
flooding near you", caption "Several people report flooding 3 km away. Not yet confirmed by
officials — stay alert." Button "See what's reported". Below, the same sections.
Keep amber subtle (tinted background, amber icon and title only).
```

### M3 — Home: active alert (the only screen allowed to use coral)
```
Same layout, hero card uses muted coral #C2410C only as a left 6px stripe, icon and title;
card background a very light warm tint (#FFF7ED), body text stays dark grey.
Title "Flood alert for your area", subtitle "Official NDMA alert · valid until 17:30".
Three short instruction bullets: "Move to higher floors", "Avoid Sinhagad Road",
"Keep phone charged". Two buttons: solid teal "I'm safe" and outline "Why this alert?".
Small line: "Verified by: NDMA alert + 142 mm rain recorded + local news".
A subtle sound/vibration indicator chip "Alert sound on" with a mute toggle.
Do NOT make the whole screen red; it must feel serious but calm.
```

### M4 — Why this alert / evidence (mobile)
```
SachVerify design system, mobile. Screen "Why this alert?".
Header back arrow + title. Status pill "Verified · Current".
Plain summary in 2 sentences.
Stacked evidence cards (one per source): source name + type tag, time ago, distance,
2-line verbatim excerpt, "Open ↗". Order: Official, Sensor, Local news.
Collapsible "What isn't confirmed" with one unverified fact in muted text.
Mini map card at the bottom showing alert area outline and the user's dot.
```

### M5 — Check a message (mobile tipline)
```
SachVerify design system, mobile. Screen "Check a message".
Large paste box "Paste a forwarded message or link", buttons "Paste" and "Add photo/video".
Below, after checking, a result card: status pill "Conflicting", headline
"Dam burst is not confirmed", 2-line reason, "Seen 23 times today", buttons
"See evidence" and "Share result" (share icon). Calm loading state with a thin progress bar
and steps text. Copy must be non-alarming and simple enough for a non-technical citizen.
```

### M6 — Map (mobile)
```
SachVerify design system, mobile. Full-screen light map of Pune with the user location dot,
one official alert area outline, small status-coloured claim dots with clusters.
Bottom sheet (peek height 30%): "Near you" list with the same rows as Home.
Top: segmented filter "All · Verified · Watch". Floating recenter button.
```

### M7 — Onboarding + permissions
```
SachVerify design system, mobile, 3-step onboarding.
Step 1: "Verified alerts, not rumours" with a simple line illustration of a shield and a check.
Step 2: "Choose your area" — search field + "Use my location" button; privacy note
"Your exact location stays on your phone."
Step 3: "Turn on alert sound" — explains that sound plays only for official or verified threats;
buttons "Enable alerts" and "Not now". Progress dots at the bottom. Minimal, airy.
```

---

## Hand-off notes for implementation
- When exporting from Stitch, keep the **colour tokens and status pill** exactly. The frontend maps them to `StatusBadge`, `EvidenceItem`, `PropositionRow`, `ThreatBanner` and `RumourCard` (PRD §16).
- Prefer **HTML/Tailwind export** from Stitch. React components are built from that in the repo.
- Sample text in these prompts is mock content. Real screens bind to `/api/stories`, `/api/claims/{id}`, `/api/beacon/{id}/status`, `/api/eval/latest`.
