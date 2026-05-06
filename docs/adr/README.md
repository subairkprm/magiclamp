# Architecture Decision Records (ADRs)

Short, dated records of architecturally significant decisions. Format follows
Michael Nygard's classic ADR template (Context → Decision → Consequences).

| # | Title | Status |
|---|-------|--------|
| [0001](0001-brain-router-split.md) | Split `brain/api/v1/brain.py` into a per-feature package | Accepted |
| [0002](0002-desktop-consolidation.md) | Archive `spreadverse-desktop/`; canonical client is `desktop/` | Accepted |
| [0003](0003-sse-streaming-ask.md) | Server-Sent Events for the streaming Ask flow | Accepted |
| [0004](0004-design-tokens-and-rtl.md) | CSS-variable design tokens + LTR/RTL switch | Accepted |
| [0005](0005-pluggable-llm-providers.md) | Pluggable LLM provider layer (`brain/core/llm/`) | Accepted |
| [0006](0006-sqlite-default-backend.md) | SQLite as the default internal database backend | Accepted |
