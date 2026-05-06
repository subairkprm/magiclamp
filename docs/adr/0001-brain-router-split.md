# ADR 0001 — Split `brain/api/v1/brain.py` into a per-feature package

- **Status:** Accepted
- **Date:** 2026-05
- **Deciders:** Lead Architect
- **Tags:** backend, refactor, hot-file

## Context

The Brain HTTP layer was a single 715-LoC FastAPI router file
(`brain/api/v1/brain.py`) owning **memory**, **reasoning** (lead/ask/decide),
**training**, **change-log** and **scheduler** endpoints, plus an in-process
task store, an LLM client and a fact cache. Symptoms:

- High change risk: any new endpoint touched the same file.
- Low cohesion: unrelated concerns (training export, scheduler triggers, LLM
  prompting, task bookkeeping) were interleaved.
- Hard to test: helpers were private to the module so unit tests had to import
  via the public router rather than the helper directly.
- Blocked the streaming-Ask & threads roadmap, which would have pushed the
  file past 1k LoC.

## Decision

Move the implementation into a package, `brain/api/v1/_brain/`, with one
module per feature area and a shared `services.py` for cross-cutting helpers
(LLM client, in-process task store, fact cache, common dependencies):

```
brain/api/v1/
├── brain.py            # thin shim:  from ._brain import router
└── _brain/
    ├── __init__.py     # composes the parent router
    ├── services.py     # llm(), llm_stream(), task store, fact cache
    ├── memory.py       # remember / recall / observe / events / stats
    ├── reason.py       # lead / ask / ask-stream / decide / self-analyse / tasks
    ├── training.py     # stats / add / export
    ├── changes.py      # record / history
    └── scheduler.py    # jobs / run
```

The legacy import path `from api.v1 import brain` is preserved by re-exporting
`router` from the shim, so `brain/main.py` (and any external code) needs no
change.

## Consequences

### Positive
- Each feature module is < 200 LoC and independently testable.
- The streaming endpoint (`POST /brain/reason/ask/stream`) was added without
  growing the original file.
- Public route paths and behaviour are byte-identical (verified by
  `tests/test_brain_split.py::test_all_legacy_brain_endpoints_still_registered`).
- Test coverage went from **59 / 62** to **66 / 66** (the 3 known
  `TestAPIKeys` failures were fixed in the same PR; see ADR 0001 follow-up).

### Negative
- Two import shapes coexist (`api.v1.brain` and `api.v1._brain`). The shim is
  intentionally tiny and documented so this should not confuse readers.
- The in-process task store is still module-level state. A production-grade
  swap (e.g. Redis) is now well-isolated in `services.py` for a future ADR.

## Alternatives considered

1. **Leave it as-is.** Rejected: the file was already a hot-path bottleneck.
2. **Split inside the same file** with section comments. Rejected: doesn't fix
   the testability or change-risk problems.
3. **Move to FastAPI sub-applications.** Rejected: heavier than necessary;
   `APIRouter` composition is idiomatic and sufficient.
