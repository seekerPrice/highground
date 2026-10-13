# Dashboard refinement — Tasks20–22

The user explicitly requested a responsive, well-designed and creative dashboard. This is an authorized visual refinement of the existing local product, including Task22; it adds no flood features or data claims. Astra read the frontend-design skill, web/AGENTS.md and the actual dashboard/CSS before this plan. The frontend owner must read relevant installed Next documentation before implementation.

## Direction and tokens

HighGround is a neighbourhood response board for small shops in Taman Sri Muda. Its distinctive element is the working map connected to shop selection and a chronological activity rail. Spend visual emphasis there; keep evidence qualifications and controls quiet, legible and accessible.

- Rain paper `#F3F8FB`: page/background; white map and content surfaces.
- Harbour ink `#17324D`: primary text and structural headings.
- River teal `#117C83`: selection, navigation and focus.
- Watch ochre `#9A6700`, Warning orange `#B6481A`, Danger red `#AF1F39`: semantic status only, with words and marker shapes.
- Retain the existing locally bundled Source Sans 3 at weights400/600/700 (imported by web/app/layout.tsx), with its system fallback, tabular numerals and a restrained scale: fluid32–48px place title,22–26px section titles,16px body,14px annotations. No remote font request or new library.
- Left alignment,8px spacing rhythm,44px controls, visible focus and readable contrast on actual backgrounds. Long labels wrap; tables scroll inside their own labelled region. No decorative animation; respect reduced motion.

## Layout

```text
HighGround        Neighbourhood / Recovery / Feedback       Simulation
Taman Sri Muda                 Official-source status + checked time
Reported actions and accepted/virtual delivery, with definitions
┌─────────────────────────────────────┬────────────────────┐
│ Functional neighbourhood map        │ Latest activity    │
│ legend + selected shop context      │ level/time/reason  │
└─────────────────────────────────────┴────────────────────┘
Shops and historical destinations (usable without map gestures)
Recovery: waste by confirmed street + policy coverage
Owner water reports, coverage and constrained calibration trend
Operator controls / bounded result state / emergency footer
```

On desktop, the map occupies most width and the activity rail is narrower. On tablet, maintain hierarchy rather than squeezing the rail into unreadable columns. On390px and320px phones, compact the source summary and metric strip, give the map a useful bounded height, then show selected shop/activity and recovery/feedback sections. Section anchors can reduce scrolling; do not replace accessible lists with map gestures. Keep current statuses and unknown coverage visible even if secondary definitions/details collapse.

## Critique before implementation

The current UI already has appropriate colours and a real map, but long equally weighted sections push the map down, repeated outcome grids make policy and response data compete, and large unavailable values crowd narrow layouts. Adding another identical metric card row for Task22 would repeat a generic dashboard pattern. Revise to one clear geographic focal point, a compact measured-action strip, a chronological rail and distinct recovery/feedback sections. Use spatial and temporal relationships as structure; no invented district outlines, numbered decorations, marketing hero, loud gradients or all-caps labels.

Keep the status distinction precise: unavailable does not mean no flood; accepted does not mean read; virtual and seeded history remain labelled; response coverage is not accuracy. Preserve exact stock-value definitions, policy uncertainty, waste exclusions and the fixed food warning. Operator token handling and request-retry identities remain unchanged.

## Ownership and checks

After Task22 store contracts are handed off, Sol task1 owns the frontend polish and Task22 panel exclusively. Sol recovery owns shared backend integration. Proposed changes: dashboard-view, neighbourhood map styling only where needed, waste-summary, a new outcome-summary component/DTO tests, and CSS under a dashboard-specific wrapper. Avoid global element rules that alter report/print. No dependency or lockfile change is expected.

Before building, Sol records any refinement to this plan and its brief-specific critique. Pure contract/interaction checks, TypeScript and lint run locally; root coordinates the production build and actual browser. Verify desktop, tablet,390px and320px; keyboard order/focus; selection/list parity; reduced motion; long labels; available/empty/partial/unavailable states; no page overflow; correct bounded operator retries. Inspect screenshots and actual contrast. Preserve the already-passed protected report/receipt/PDF flow by scoping every new rule to the dashboard. Rerun affected report/print checks only if an actual shared-style change warrants it; an external native print stall is not automatically an application defect.

No visual or Task22 acceptance is claimed by this plan. Final local gate and independent Matt Standards/Spec reviews remain required against baseline1646ebc.
