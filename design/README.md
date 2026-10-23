# SachVerify UI designs (Google Stitch export)

12 screens generated in Google Stitch from `docs/STITCH_UI_PROMPTS.md`, with the colour rules replaced by [design_system.md](design_system.md).

- **Stitch project:** "SachVerify", id `18004204217703114445`
- **Stitch design system asset:** `assets/11828734128776249430` ("SachVerify Minimal")
- **Style:** white and greys, hairline borders, Inter + JetBrains Mono. One accent, deep teal `#0F766E`, used only for primary buttons, links, selected states and the active nav item. Status colours appear only as 6px dots inside white outline pills.

Each screen has a `.html` file (Tailwind CDN + inline `tailwind.config`, ready to port to React + Tailwind) and a `.png` screenshot.

## Desktop: responder Console (1440px)

| Screen | Stitch screen id | Files |
|---|---|---|
| D1 Console (stories + map + evidence) | `1002900a4a0a4f36aa7af1729b93985d` | [D1_console.html](desktop/D1_console.html), [.png](desktop/D1_console.png) |
| D2 Story detail (reasoning view) | `3533f6e28e5647be8e2af8cd04f87db9` | [D2_story_detail.html](desktop/D2_story_detail.html), [.png](desktop/D2_story_detail.png) |
| D3 Check a post (modal) | `4ec7219ce19048b889dd3097db086cd7` | [D3_check_post.html](desktop/D3_check_post.html), [.png](desktop/D3_check_post.png) |
| D4 Evaluation | `02137298e08047b3aedccce0b0198d77` | [D4_evaluation.html](desktop/D4_evaluation.html), [.png](desktop/D4_evaluation.png) |
| D5 Benchmark review | `3e590990a4cb47008bac033203b25e37` | [D5_review.html](desktop/D5_review.html), [.png](desktop/D5_review.png) |

## Phone: Beacon citizen app (390px)

| Screen | Stitch screen id | Files |
|---|---|---|
| M1 Home: all clear | `6418e9a6d28b4d16b935871bd034d787` | [M1_home_all_clear.html](mobile/M1_home_all_clear.html), [.png](mobile/M1_home_all_clear.png) |
| M2 Home: watch | `880d221d36bf46e2a63a765c7dfe67a5` | [M2_home_watch.html](mobile/M2_home_watch.html), [.png](mobile/M2_home_watch.png) |
| M3 Home: active alert | `c7f79631677d4209bf416a86a18b095a` | [M3_home_alert.html](mobile/M3_home_alert.html), [.png](mobile/M3_home_alert.png) |
| M4 Why this alert? | `a69ed959c4ac4049ba180f60990fb85d` | [M4_why_alert.html](mobile/M4_why_alert.html), [.png](mobile/M4_why_alert.png) |
| M5 Check a message | `587df147168c4c9f9553924bda118c66` | [M5_check_message.html](mobile/M5_check_message.html), [.png](mobile/M5_check_message.png) |
| M6 Map | `7fae711f663943279b393b397b928ae1` | [M6_map.html](mobile/M6_map.html), [.png](mobile/M6_map.png) |
| M7 Onboarding (step 2 of 3) | `f482e621dada4e7a87a44c0e92c1347e` | [M7_onboarding.html](mobile/M7_onboarding.html), [.png](mobile/M7_onboarding.png) |

## Notes for implementation

- **Teal accent on 9 screens was applied locally.** The design was first generated near-monochrome (black buttons). After feedback that it was too bare, teal was added. Stitch saved new teal copies of M1, M2 and M5, so those files are Stitch's own output. For D1–D5, M3, M4, M6 and M7, Stitch applied the teal only inside its editor and the API kept serving the black versions. So the same changes were applied to the exported HTML with a script, and those 9 PNGs were re-rendered locally with headless Chrome. In the Stitch project those 9 screens may still look black.
- **The Stitch project has extra screens:** duplicate M1, M3, M4 and D1 drafts, plus the original black M1, M2 and M5. Only the ids above are the chosen versions.
- **The screens use sample data.** D4 shows invented metric values (Macro-F1 0.91 and so on), not placeholders. Bind everything to `/api/stories`, `/api/claims/{id}`, `/api/beacon/{id}/status` and `/api/eval/latest`. Never ship these numbers.
- **Known layout issues to fix when porting:**
  - On M1–M3 the floating "Check a message" pill overlaps the last list row.
  - Stitch used Material Symbols icons; swap them for Lucide.
  - Stitch's `tailwind.config` carries generated Material-style colour names (`primary`, `surface-container`…). Map them to the tokens in `design_system.md` rather than copying them.
- Components to extract (PRD §16): `StatusBadge` (white outline pill + dot), `EvidenceItem`, `PropositionRow`, `ThreatBanner` (M1–M3 hero card), `RumourCard`.
