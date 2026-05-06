# ADR 0004 — CSS-variable design tokens + LTR/RTL switch

- **Status:** Accepted
- **Date:** 2026-05
- **Tags:** desktop, ui, accessibility, i18n, rtl

## Context

The desktop UI was a flat collection of Tailwind utility classes hard-coded
to dark slate colors (`bg-slate-950`, `text-slate-100`, …). This made it
impossible to:

- ship a light theme without editing every file,
- support Arabic right-to-left layout for the UAE banking domain,
- present a coherent component library that page authors can compose.

## Decision

1. **Define design tokens as CSS custom properties** in `src/index.css`:

   ```css
   :root {
     --ml-bg, --ml-surface, --ml-elevated, --ml-border, --ml-muted,
     --ml-fg, --ml-fg-muted, --ml-accent, --ml-accent-fg,
     --ml-danger, --ml-success, --ml-warning,
     --ml-radius, --ml-motion;
   }
   .theme-light { /* override the palette tokens */ }
   ```

2. **Map tokens into Tailwind** (`tailwind.config.js`) so existing utility
   syntax keeps working: `bg-bg`, `text-fg`, `border-border`, etc.

3. **Pick the active theme** by setting `theme-light` or `theme-dark` on
   `<html>`. With no class, the page honours the OS `prefers-color-scheme`.

4. **Toggle LTR/RTL** via `document.documentElement.dir` and a `dir-rtl`
   class. A `ThemeToggle` primitive in the sidebar persists both the theme
   and the direction in `localStorage`.

5. **Respect `prefers-reduced-motion`** — token-driven motion duration drops
   to ~0 ms when the user has reduced motion enabled, and a global
   `*` rule shortens any remaining transitions.

6. **Ship a UI primitives package** under `desktop/src/components/ui/`:
   `Button`, `Spinner`, `Skeleton`, `EmptyState`, `ErrorBoundary`,
   `ThemeToggle`. All consume tokens, never hard-coded slate values.

## Consequences

### Positive
- Light/dark/RTL ship today; later themes (high-contrast, banking-brand) add
  one CSS class.
- Pages stop owning visual decisions — they compose primitives instead.
- Accessibility baseline raised: visible focus ring on every interactive
  element, reduced-motion respected, citation chips are real `<button>`s with
  `aria-label`s carrying the source key.

### Negative
- Existing utility classes (`bg-slate-900`, `text-slate-100`) are still in
  the codebase. A future PR should sweep them to the token names. Current
  pages still render correctly because tokens default to the same dark palette.
