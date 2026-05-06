import Spinner from './Spinner.jsx'

/**
 * Token-driven Button primitive.
 *
 * Variants map to the design-system roles (primary / secondary / ghost /
 * danger). Loading state both disables the control and announces it via
 * aria-busy so assistive tech users get the change.
 */
export default function Button({
  children,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  iconLeft,
  className = '',
  ...rest
}) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg font-medium ' +
    'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ' +
    'disabled:opacity-50 disabled:cursor-not-allowed'
  const sizes = {
    sm: 'text-xs px-2.5 py-1',
    md: 'text-sm px-4 py-2',
    lg: 'text-base px-5 py-2.5',
  }
  const variants = {
    primary:   'bg-brand-600 hover:bg-brand-500 active:bg-brand-700 text-white',
    secondary: 'bg-elevated hover:bg-border active:bg-muted text-fg',
    ghost:     'bg-transparent hover:bg-elevated text-fg',
    danger:    'bg-red-700 hover:bg-red-600 active:bg-red-800 text-white',
    subtle:    'bg-transparent text-fg-muted hover:text-fg hover:bg-elevated',
  }
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
      {...rest}
    >
      {loading ? <Spinner size={14} /> : iconLeft}
      {children}
    </button>
  )
}
