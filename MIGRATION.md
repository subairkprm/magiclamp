# Migration Guide

## Desktop client consolidation — `spreadverse-desktop/` → `desktop/`

> **TL;DR** — `desktop/` is now the only supported MagicLamp desktop client.
> `spreadverse-desktop/` remains in version control for history but is no
> longer built, tested or deployed. See
> [ADR 0002](docs/adr/0002-desktop-consolidation.md) for the rationale.

### Who is affected?

You only need to do anything if you currently:

- run a local Tauri build of `spreadverse-desktop/`, or
- maintain CI/packaging that targets `spreadverse-desktop/`.

If you already use the Electron `desktop/` app, **no action is required**.

### Migration steps

1. Stop running the old client. Uninstall any locally-built Tauri binaries.
2. Build & launch the canonical client:

   ```bash
   cd desktop
   npm install
   npm run dev
   ```

3. Sign in again with the same credentials. Tokens are stored per-app, so
   you'll need to log in once in the new client. There is no fact / memory
   migration to do — both clients pointed at the same Brain API and Supabase
   instance, so all server-side data is already available.

4. If you have custom packaging or CI that referenced `spreadverse-desktop/`,
   update the path. The build commands in `desktop/` are:
   - `npm run build:ui`     — Vite production bundle
   - `npm run build`        — full Electron installer (electron-builder)

### What stays the same

- The Brain HTTP API — every `/api/v1/brain/*` route, every JWT/API-key flow,
  every Supabase table.
- All RAG behaviour (`docs/rag.md`).
- Streaming Ask works in `desktop/` from this release on (see
  [ADR 0003](docs/adr/0003-sse-streaming-ask.md)).

### Reverting

If a regression in `desktop/` blocks your work, you can keep building
`spreadverse-desktop/` from a previous commit. We will not patch issues in
that tree going forward.
