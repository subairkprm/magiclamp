# ADR 0002 — Archive `spreadverse-desktop/`; canonical client is `desktop/`

- **Status:** Accepted
- **Date:** 2026-05
- **Tags:** desktop, consolidation, spreadverse

## Context

The repository contained two parallel desktop applications:

| Path                   | Stack                          | Role |
|------------------------|--------------------------------|------|
| `desktop/`             | Electron 31 + React 18 + Vite 5 | Active development, tied to the live Brain API |
| `spreadverse-desktop/` | Tauri + React + TypeScript      | Earlier experimental variant |

Maintaining both effectively doubles every UI change and confuses new
contributors who do not know which app to install or extend.

## Decision

`desktop/` is the canonical MagicLamp client. `spreadverse-desktop/` is
**archived in place**: the directory remains in version control for
historical reference but is no longer built, deployed or tested. A
`spreadverse-desktop/ARCHIVED.md` file at the root of that directory makes the
status obvious in any file browser, and the project root `MIGRATION.md`
documents the move for users.

If a feature from `spreadverse-desktop/` (e.g. a particular Tauri integration)
is later needed in `desktop/`, port it explicitly via a normal PR rather than
reactivating the parallel app.

## Consequences

### Positive
- One desktop app to build, ship, document and secure.
- All UI/UX work in this overhaul (design tokens, primitives, streaming chat,
  citation chips, theme/RTL toggle) lands in one place.

### Negative
- Anyone running the old Tauri build needs to migrate; the
  `MIGRATION.md` describes the (small) data path: tokens are stored in
  the OS keychain in both apps and require no migration.

## Alternatives considered

- **Delete `spreadverse-desktop/`.** Rejected: keeping the source in tree
  preserves history without imposing maintenance cost, and makes future
  cherry-picks possible.
- **Promote `spreadverse-desktop/`.** Rejected: it is less complete and uses
  Tauri, which currently lacks parity with the Electron build's auto-update,
  signing and packaging story.
