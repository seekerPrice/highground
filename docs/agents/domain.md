# Domain docs

Before relevant work, read CONTEXT.md and applicable docs/adr entries if present. Missing documents are not an error; create them lazily when domain terms or architectural decisions are actually resolved.

Use a single context for HighGround. CONTEXT.md is a glossary only: actors, concepts, relationships and explicitly distinguished terms. It contains no implementation plan or technical configuration. Reuse its vocabulary in specs, tickets and tests.

Create an ADR only for a hard-to-reverse decision with a meaningful trade-off that would otherwise surprise a future reader. Flag conflicts rather than silently overriding an ADR. Planning proposals remain proposals until agreed.
