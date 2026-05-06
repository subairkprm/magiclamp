/**
 * Renders an answer string with `[#n]` citation markers replaced by
 * accessible chips that map back to the server-supplied citation list.
 *
 * Server contract (from `/brain/reason/ask` and `…/ask/stream`):
 *   citations: [{ id: number, key: string }]
 *   answer:   "...the score is 75 [#1] and the salary band [#2]..."
 *
 * Chips:
 *   • are buttons (focusable, keyboard-activatable)
 *   • carry `title`/`aria-label` with the originating fact key
 *   • emit `onCitationClick(id, key)` so callers can scroll the source panel
 */
export default function CitedAnswer({ text = '', citations = [], onCitationClick }) {
  if (!text) return null
  const map = Object.fromEntries((citations || []).map((c) => [c.id, c.key]))

  // Split on `[#n]`, keeping the matched markers as separate tokens.
  const parts = text.split(/(\[#\d+\])/g)
  return (
    <p className="text-fg leading-relaxed whitespace-pre-wrap">
      {parts.map((part, i) => {
        const m = part.match(/^\[#(\d+)\]$/)
        if (!m) return <span key={i}>{part}</span>
        const id = Number(m[1])
        const key = map[id]
        if (!key) return <span key={i} className="text-fg-muted">{part}</span>
        return (
          <button
            key={i}
            type="button"
            className="citation-chip"
            title={`Source #${id}: ${key}`}
            aria-label={`Source ${id}, fact ${key}`}
            onClick={() => onCitationClick?.(id, key)}
          >
            #{id}
          </button>
        )
      })}
    </p>
  )
}
