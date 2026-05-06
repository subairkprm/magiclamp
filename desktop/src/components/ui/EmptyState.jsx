/** Standardised empty-state used by lists, search results and chat placeholders. */
export default function EmptyState({
  icon = '🪄',
  title = 'Nothing here yet',
  hint,
  action,
  className = '',
}) {
  return (
    <div
      role="status"
      className={`text-center py-10 px-6 border border-dashed border-border rounded-xl bg-surface/50 ${className}`}
    >
      <div className="text-3xl mb-2" aria-hidden="true">{icon}</div>
      <p className="text-fg font-medium">{title}</p>
      {hint && <p className="text-fg-muted text-sm mt-1">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
