# SachVerify — design system (minimal)

Revision 2 (user feedback "too minimalistic"): added one teal accent for interactive elements.

This replaces the colour guidance in `docs/STITCH_UI_PROMPTS.md` Prompt 0. It is prepended to every Stitch screen prompt.

```
DESIGN SYSTEM — "SachVerify". Strictly minimal, near-monochrome, quiet and factual.
Think Linear / Vercel dashboard in light mode: white, greys, black text, hairline borders.

COLOUR (hard rules)
- Page background #FFFFFF. Subtle surface #FAFAFA. Borders/dividers #E5E5E5 (1px only).
- Text: primary #171717, secondary #525252, muted #A3A3A3.
- ONE accent: deep teal #0F766E. Used only for primary buttons (solid teal, white text), text links,
  focus rings, selected chips/tabs/segments, the active bottom-nav item and selected-row left borders.
  Nothing else is teal: no teal backgrounds, cards, headers or icons.
- Secondary button: white with 1px #E5E5E5 border, #171717 text.
- Status colours are used ONLY as a 6px dot inside a status pill, or as a map dot. Never as text
  colour for paragraphs, never as backgrounds, banners, card fills, stripes or large areas.
    Verified    dot #5F7F68 (muted sage)
    Conflicting dot #A88442 (muted ochre)
    Outdated    dot #A3A3A3 (grey)
    Unverified  dot #6B7A99 (muted slate blue)
    Alert (phone only) dot #9C4F3A (muted rust) — still only a dot/icon, never a fill.
- No red, no bright blue, no bright green. No gradients, no tinted cards, no coloured headers.
- Map: very light grey basemap, desaturated. Alert areas = thin 1px dark-grey outline with 4% grey fill.

TYPOGRAPHY
- Inter for all text. Sizes 28 / 20 / 16 / 14 / 12. Headings 600, body 400.
- Numbers, timestamps, IDs: JetBrains Mono 12–13px, tabular.
- Sentence case. Only tiny 11px uppercase labels with +0.06em letter-spacing, colour #A3A3A3.

COMPONENTS (identical on every screen)
- Status pill: rounded-full, white background, 1px #E5E5E5 border, 12px text #171717,
  a 6px status-coloured dot before the label. Example: (• Verified). Height 22px.
- Confidence: 2px grey track, #525252 fill, with "High / Medium / Low" text in 12px.
- Card: white, 1px #E5E5E5 border, 8px radius, 16–20px padding, no shadow.
- Evidence item: source name (14px 600) + source-type tag (grey outline tag: Official / Sensor /
  Local news / National / Post), mono timestamp + relative age, location line, 2-line verbatim
  excerpt with a 2px #E5E5E5 left rule, "Open source ↗" text link.
- Proposition row: sentence + tiny grey tags (core/detail) + state glyph ✓ ✕ ? ⟲ in #525252.
- Tags/chips: 1px #E5E5E5 outline, 12px #525252 text. Selected chip: #0F766E border and text.
- Icons: Lucide outline, 1.5px stroke, 16–18px, #525252.
- Empty/uncertain states: calm grey text, e.g. "Not enough evidence yet".

RULES
- Include only what the screen needs. No decorative illustrations, no hero images, no stock photos,
  no emojis, no avatars with photos (use initials in a grey circle), no shadows, no glassmorphism.
- Generous whitespace, clear alignment, 8px spacing grid.
- Copy is plain and non-alarming: "Not confirmed", never "FAKE".
- Output must be clean semantic HTML + Tailwind utility classes.
```
