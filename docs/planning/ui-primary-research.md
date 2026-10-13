# UI refinement: primary research

Research date: 13 October 2026. Read-only application research; no application changes or local service calls. This note recommends work and does not establish that HighGround has passed any new UI checks. The delegated researcher read the research skill; this delegation fulfills its background-research requirement.

## Competition evidence and authority

The official [themes and requirements](https://aibuildercup.com/themes.html) page specifies a working prototype, Google AI models or the described agentic platforms, Cloud Run/Firebase deployment, PDF deck, and English submission materials. Sustainability & Social Impact explicitly covers societal/environmental challenges, resource efficiency, accessibility, resilience and community support. Its category-specification bullet inconsistently lists Healthcare/Education/Sustainability/Accessibility/Social Good despite the six themes elsewhere on the same page. Treat that as a website inconsistency, not a reason to change the user's confirmed portal category.

The [official FAQ](https://aibuildercup.com/Faqs.html) independently requires a working deployed link, public GitHub repository, a video **under three minutes**, and a deck. It confirms the same weights across all themes:

| Criterion | Weight |
| --- | ---: |
| Technical merit and Gen AI implementation | 40% |
| Problem alignment and impact | 25% |
| Innovation and creativity | 25% |
| User experience and solution design | 10% |

The user has confirmed portal category **GGSI Sustainability & Social Impact**, a meaningful environmental/societal challenge involving resilience/community/waste/resource use, suggested technologies rather than a requirement to use every suggestion, and deadline **19 October 2026, 02:29 MYT**. These portal details and exact deadline are user-provided evidence, not independently accessed portal facts. Root's hosting deferral remains authoritative; eventual deployed acceptance is still needed for submission, but this research authorizes no hosting.

## Five recommended actions

1. **Make one judge journey legible before expanding visual scope.** Proposed emphasis: a clearly labelled synthetic flood observation → meaningful Gemini interpretation → deterministic priority/actions → confirmed response → defensible recovery/waste estimate. Show where AI contributes and where fixed safety rules take over. This is our inference from the judging weights, not a new feature requirement. A beautiful dashboard alone leaves the dominant technical/impact criteria under-evidenced. Preserve the approved limits: no avoided-loss claim, no guaranteed safe route, and no simulation disguised as live coverage.

2. **Use a bounded screenshot → critique → fix → recheck loop.** Provide the implementing agent with the existing design direction, actual screenshots and explicit success criteria, then use an independent rendered review. The user’s latest instruction assigns Astra the current implementation and design decisions; root verifies the browser result. First record the three most consequential defects, then fix those and re-capture identical states/viewports. Two focused rounds are a practical project recommendation, not a researched universal optimum. Anthropic's [official best practices](https://code.claude.com/docs/en/best-practices) explicitly recommend screenshot comparison and observable pass/fail checks. Its [frontend harness experiment](https://www.anthropic.com/engineering/harness-design-long-running-apps) supports separate generator/evaluator roles, concrete design/functionality criteria, and interaction with the running page. It also reports lenient self-evaluation, complexity growth and cases where intermediate iterations beat the final result. Keep the best baseline; do not endlessly chase an AI aesthetic score. This evidence concerns Anthropic's experiments, not a measured guarantee for Astra/Sol.

3. **Test comprehension and interaction, not screenshots alone.** Proposed local matrix: desktop, tablet, 390px and 320px; keyboard-only navigation; enlarged text; reduced motion; loading, empty, stale/unavailable, error and long-label states. Ask whether the first screen answers what happened, how current the evidence is and what action matters. WCAG 2.2 requires keyboard access, visible focus, text contrast generally 4.5:1 (3:1 for large text), and information conveyed beyond colour. [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

   For normal vertically scrolling content, assess reflow at 320 CSS pixels without two-dimensional scrolling; maps and necessary data tables have exceptions, but surrounding controls do not inherit them. [W3C reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) Sticky elements must not fully hide focused controls. [W3C focus guidance](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) WCAG AA target size is generally 24×24 CSS pixels or qualifying spacing, with exceptions; 44×44 is a useful project touch target, not the AA minimum. [W3C target-size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) Ensure consequential asynchronous status changes are programmatically available without moving focus; avoid announcing every feed update. [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) These checks support accessibility; they do not establish full WCAG conformance.

4. **Treat shadcn as an optional component source, not the design strategy.** Its [official introduction](https://ui.shadcn.com/docs) describes editable component code, composable interfaces and distribution of code with dependencies. It does not eliminate ownership or integration work. Recommendation: preserve the current stack and dependencies; use native semantic elements and existing components for this polish pass. Only consider a specific component if an evidenced interaction gap justifies its maintenance/dependency cost and stack compatibility. A migration is not necessary to achieve the approved map-led identity. Any copied component still needs the actual theme, labels, focus flow and mobile behaviour verified.

5. **Build the submission around observable proof and explicit limits.** Recommendation: record the complete functioning journey rather than disconnected screen tours; keep the public demo synthetic and private evidence private. Use the PDF/video to explain meaningful AI, community value, differentiation and operational feasibility with measured results where available. Reserve time for a hosted-link smoke test once hosting is authorized. Keep website-confirmed submission requirements and user-confirmed portal details distinct; do not infer current hosting, repository visibility or submission completion from this note.

## Blind spots to carry into independent review

- A polished map can imply live operational coverage: simulation, source age and unavailable status must remain prominent.
- Screenshot review misses keyboard traps, failed asynchronous actions, screen-reader status and misleading data semantics.
- AI art-direction scores do not measure whether a stressed shop owner or first-time judge understands the next step.
- Adding every suggested technology increases integration risk without proving meaningful AI use.
- Local success is not a working public submission URL; deployment remains a separate pending acceptance gate.

These are review hypotheses and recommendations, not claims that the current app exhibits each defect.
