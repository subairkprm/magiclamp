# Changelog

All notable changes to MagicLamp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Streaming Ask endpoint** `POST /api/v1/brain/reason/ask/stream` (SSE) emitting
  `meta` (citations) → `token`* → `done` events. Reuses the same retrieval and
  prompt path as `/brain/reason/ask`. See
  [docs/reference/streaming-ask.md](docs/reference/streaming-ask.md) and
  [ADR 0003](docs/adr/0003-sse-streaming-ask.md).
- **Brain router split** — `brain/api/v1/brain.py` (715 LoC) was decomposed
  into a focused package `brain/api/v1/_brain/` with one module per feature
  area (memory, reason, training, changes, scheduler) and a shared
  `services.py`. The legacy import `from api.v1 import brain` keeps working.
  See [ADR 0001](docs/adr/0001-brain-router-split.md).
- **Design tokens & UI primitives** in the desktop app: CSS-variable token
  layer with light/dark themes and an LTR/RTL switch (Arabic ready),
  consumed by new primitives `Button`, `Spinner`, `Skeleton`,
  `EmptyState`, `ErrorBoundary` and `ThemeToggle` under
  `desktop/src/components/ui/`. See [ADR 0004](docs/adr/0004-design-tokens-and-rtl.md).
- **Streaming chat surface** — the Ask tab now streams tokens, renders
  inline citation chips wired to server-supplied retrieved keys, and
  exposes Copy / Regenerate / Stop controls with graceful fallback to the
  polled task pipeline.
- **App-level `ErrorBoundary`** so render-time crashes recover instead of
  showing a blank screen.
- **Diátaxis docs scaffold** under `docs/`: `tutorials/`, `how-to/`,
  `reference/`, `explanation/`, `adr/`, plus a quickstart and an API surface
  map. ADRs 0001–0004 record the structural decisions in this release.
- **`MIGRATION.md`** documenting the desktop consolidation.
- New backend tests in `tests/test_brain_split.py` (4 tests) guarding the
  router shim, the legacy endpoint surface and the SSE wire format.

### Changed
- `core/auth.py::generate_api_key` and `verify_api_key` now go through the
  `DatabaseClient` abstraction (`get_database_client()`) instead of opening
  a raw Supabase client. This unblocks unit-testing without a network
  Supabase reachable from CI.
- Sidebar now renders the `ThemeToggle` so the theme + direction can be
  switched at runtime.

### Fixed
- The 3 pre-existing `tests/test_auth.py::TestAPIKeys` failures
  (`test_api_key_generation`, `test_api_key_verification_success`,
  `test_api_key_verification_failure`). Backend test suite now passes
  **66 / 66** (previously 59 / 62).

### Deprecated
- `spreadverse-desktop/` is archived in place (see
  [`MIGRATION.md`](MIGRATION.md) and
  [ADR 0002](docs/adr/0002-desktop-consolidation.md)). Future desktop work
  lands in `desktop/`.
