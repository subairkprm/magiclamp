/** Accessible inline spinner. Honours `prefers-reduced-motion` via CSS tokens. */
export default function Spinner({ size = 16, className = '' }) {
  return (
    <svg
      role="img"
      aria-label="Loading"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={`animate-spin ${className}`}
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
    </svg>
  )
}
