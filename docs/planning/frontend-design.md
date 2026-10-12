# Frontend direction for Tasks 13 and 15

Prepared with the frontend-design skill. This is a design brief for Astra's later task planning, not completed UI or permission to skip the Must dependencies. Preserve Next.js, Tailwind and Leaflet. No extra component library is needed.

## Subject and primary job

HighGround helps a small shop owner understand flood preparation and record recovery estimates. The public dashboard demonstrates a neighbourhood response with synthetic shops; the bearer report helps one owner inspect an estimated loss and its supporting media. A visitor must distinguish simulations, unavailable observations and owner-reported actions immediately.

## Compact visual system

Six working colours: rain-paper `#F3F8FB` for the page, harbour ink `#17324D` for type, river teal `#117C83` for navigation and selected places, Watch ochre `#9A6700`, Warning orange `#B6481A`, and Danger red `#AF1F39`. Use status words and distinct marker shapes as well as colour. Small status text stays harbour ink unless its actual foreground/background contrast passes. White is the neutral map/report surface.

Root calculated WCAG relative-luminance ratios for opaque foregrounds on paper/white: ink12.27/13.13, teal4.64/4.96, Watch4.55/4.87, Warning4.99/5.34, Danger6.38/6.82. The original brighter orange failed4.5:1 and was replaced before implementation. These calculations do not certify rendered UI: opacity, overlays, muted text, focus borders and actual backgrounds still need inspection.

Type: Source Sans 3 for the English interface, with tabular numerals for amounts and timing. Its open shapes suit small status text and dense item tables. Bundle a licensed font asset locally if practical; do not introduce a build-time dependency on a remote font request. Use the same family across headings and body, approximately16px body/24px section/36px page title. Noto Sans script fallbacks may be added where multilingual content actually appears. Final font assets and licensing are checked during implementation.

Spacing follows an8px rhythm, with clear40px minimum interactive targets and visible focus. Align content left. Rounded corners belong to controls and floating map callouts; do not turn every datum into an identical card. Keep explanatory lines under80characters. Respect reduced motion; use no decorative page-load animation.

## Dashboard composition

The defining visual is a large, functional Taman Sri Muda map alongside a narrow chronological activity list. Avoid a marketing hero. A quiet top strip contains the name, page purpose and persistent `Simulation` badge. Show official-source freshness in a separate plain status line with observation time and unavailable/stale wording. Never convert unavailable readings into a green all-clear.

```text
HighGround                 Neighbourhood demo       Simulation
Official observations: stale / unavailable   Last checked …

Estimated stock value reported lifted   Vehicles reported moved   Alerts accepted

┌────────────────────────────────┬─────────────────────────┐
│                                │ Latest activity         │
│ Taman Sri Muda map              │ Warning + reason + time │
│ Shop status, parking, shelter   │ Owner-reported action   │
│ Event radius with clear legend │ Danger + reason + time  │
│                                │                         │
├────────────────────────────────┴─────────────────────────┤
│ Selected shop: inventory estimate, actions and timestamps│
└──────────────────────────────────────────────────────────┘
Demo controls (operator access)
```

On a phone, show the source/simulation status, a compact outcome strip, a useful map height, selected shop details and then activity. Keep the same data and controls accessible without relying on map gestures. Leaflet attribution remains visible. The map alone cannot be the only way to find a shop or destination.

Outcome labels must express their evidence: stock value is an estimate tied to an exact displayed list and self-reported confirmation. Its aggregate is the maximum actually confirmed immutable snapshot per shop/episode, summed across shops; the accessible definition must explain this. A vehicle counts once per shop/episode. A Telegram API acceptance is not proof of a phone notification being read. Show definitions beside or beneath the strip. The event feed shows the attributed triage reason in plain language. Use source and timestamps rather than technical storage or agent implementation details.

Operator controls are a compact separate panel with Watch, Warning, Danger and Reset actions, clear in-flight/result states and validation errors. Public rendering contains only synthetic shops. Never place the operator token in a URL or public frontend config. Source staleness and simulation labels remain visible during an operator-triggered event.

## Report composition

Use a printable document layout: shop name, report date, prominent `Estimated loss` amount, confidence note and baseline/after comparison table. Lead with what the owner needs to inspect. Media receipts and integrity details follow the table, with hashes available in an expandable detail panel and an explicit `Verify file integrity` action. Only show `File integrity verified` after the API recomputes and matches stored bytes.

```text
HighGround / Flood loss estimate             Save as PDF
Synthetic shop name                         Simulation, if applicable
Estimated loss RM…                          Confidence / limits

Item              Before           After             Estimated loss
…

Evidence receipts  Before upload / after upload
Receipt time · attributed location · file integrity result
What this report can and cannot establish
```

Render loading, unavailable, expired/missing report and failed verification states distinctly. A bearer link grants this report's access only; media never becomes a public bucket asset. Do not imply an insurer accepted a claim or a hash establishes a recording's authenticity. Print CSS removes controls and map chrome, keeps table headers and readable page breaks, and preserves estimate/simulation/confidence attribution in the PDF.

## Review before and after building

The map presents spatial information and the adjacent list presents time-ordered activity. The report uses an item ledger so the owner can compare evidence and amounts. Colour identifies status and mapped meaning.

During implementation, inspect actual rendered desktop and narrow-phone views, keyboard focus, long shop/item names, empty/stale/failed states and printed output. Verify responsive layout and contrast from rendered results, not assumptions. Do not add Stretch map layers, insurance/accuracy metrics, waste panels or other Should features before their accepted implementation gates.
