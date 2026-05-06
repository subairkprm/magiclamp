/**
 * UI primitives — barrel export.
 *
 * Components live as small, dependency-light files under
 * `desktop/src/components/ui/` so the design system can be evolved
 * without rippling changes through every page. All primitives consume
 * the design tokens declared in `src/index.css`.
 */
export { default as Button }        from './Button.jsx'
export { default as Spinner }       from './Spinner.jsx'
export { default as Skeleton }      from './Skeleton.jsx'
export { default as EmptyState }    from './EmptyState.jsx'
export { default as ErrorBoundary } from './ErrorBoundary.jsx'
export { default as ThemeToggle }   from './ThemeToggle.jsx'
