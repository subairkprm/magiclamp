import { useRef, useState } from 'react'
import client from '../api/client'
import { useTaskPoller } from '../components/TaskPoller'
import useAskStream from '../api/useAskStream'
import CitedAnswer from '../components/CitedAnswer'

const TABS = ['Ask', 'Decide', 'Lead Analysis']

export default function Brain() {
  const [tab, setTab] = useState('Ask')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-100">AI Brain</h1>
        <p className="text-slate-500 text-sm mt-1">Reasoning engine powered by Ollama</p>
      </div>

      <div className="flex gap-2 mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`tab-btn ${tab === t ? 'active' : ''}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Ask' && <AskTab />}
      {tab === 'Decide' && <DecideTab />}
      {tab === 'Lead Analysis' && <LeadTab />}
    </div>
  )
}

// ─── Ask ──────────────────────────────────────────────────────────────────────
//
// The Ask tab uses the new SSE streaming endpoint (`/brain/reason/ask/stream`)
// to render tokens as they arrive, exposes server-side RAG citations as
// inline chips, and offers Copy / Regenerate / Stop controls.
//
// On any streaming failure we automatically fall back to the legacy polled
// task pipeline (`/brain/reason/ask` + `/brain/tasks/{id}`) so the user
// always gets an answer even when the gateway buffers or strips SSE.
function AskTab() {
  const [question, setQuestion] = useState('')
  const lastQuestion = useRef('')
  const stream = useAskStream()
  // Polled fallback path retains the existing task poller so we don't
  // re-implement task orchestration in two places.
  const { poll, result: polledResult, error: polledError, loading: polling, reset: resetPolled } = useTaskPoller()
  const [usedFallback, setUsedFallback] = useState(false)

  async function runAsk(q) {
    if (!q?.trim()) return
    lastQuestion.current = q
    setUsedFallback(false)
    resetPolled()
    await stream.ask(q)
    // Heuristic: if the stream ended with an error and produced no tokens,
    // fall back to the polled flow so the user still gets a response.
    if (stream.error && !stream.answer) {
      setUsedFallback(true)
      try {
        const { data } = await client.post('/brain/reason/ask', { question: q })
        poll(data.task_id)
      } catch (e) {
        // Both paths failed; the streaming error UI will display.
      }
    }
  }

  function submit(e) {
    e.preventDefault()
    runAsk(question)
  }

  function regenerate() {
    if (!lastQuestion.current) return
    runAsk(lastQuestion.current)
  }

  function copy() {
    const text = stream.answer || polledResult?.answer || ''
    if (text) navigator.clipboard?.writeText(text).catch(() => {})
  }

  // Decide which payload to render — streaming wins, fallback otherwise.
  const renderedText  = stream.answer || polledResult?.answer || ''
  const renderedMeta  = stream.meta || (polledResult ? {
    retrieval_mode: polledResult.retrieval_mode,
    citations: polledResult.citations || [],
  } : null)
  const isBusy   = stream.streaming || polling
  const errorMsg = stream.error && !usedFallback
    ? stream.error
    : polledError

  return (
    <div className="max-w-2xl space-y-4">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label" htmlFor="ask-input">Ask the Brain anything</label>
          <textarea
            id="ask-input"
            className="input w-full h-24 resize-none"
            placeholder="e.g. What is the best product for a customer with AED 15,000 salary?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="submit" disabled={isBusy} className="btn-primary">
            {isBusy ? <SpinnerBtn>Thinking...</SpinnerBtn> : 'Ask'}
          </button>
          {stream.streaming && (
            <button type="button" onClick={stream.stop} className="btn-secondary">Stop</button>
          )}
          {!isBusy && renderedText && (
            <>
              <button type="button" onClick={regenerate} className="btn-secondary">Regenerate</button>
              <button type="button" onClick={copy} className="btn-secondary">Copy</button>
            </>
          )}
        </div>
      </form>

      {isBusy && !renderedText && <ThinkingCard />}

      {(renderedText || renderedMeta) && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-fg-muted uppercase tracking-wider font-semibold">Answer</p>
            {renderedMeta?.retrieval_mode && (
              <RetrievalBadge mode={renderedMeta.retrieval_mode} />
            )}
          </div>

          <CitedAnswer text={renderedText} citations={renderedMeta?.citations} />

          {renderedMeta?.citations?.length > 0 && (
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-fg-muted uppercase tracking-wider font-semibold mb-1">
                Sources
              </p>
              <ul className="space-y-1">
                {renderedMeta.citations.map((c) => (
                  <li key={c.id} className="text-xs text-fg-muted">
                    <span className="citation-chip mr-1">#{c.id}</span>
                    <span className="font-mono">{c.key}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {usedFallback && (
            <p className="text-[11px] text-fg-muted italic">
              Streaming unavailable — answered via polled task fallback.
            </p>
          )}
        </div>
      )}

      {errorMsg && <ErrorCard>{errorMsg}</ErrorCard>}
    </div>
  )
}

function RetrievalBadge({ mode }) {
  const cls = mode === 'rag'    ? 'badge-green'
            : mode === 'recent' ? 'badge-blue'
            :                     'badge-yellow'
  const label = mode === 'rag'    ? 'RAG'
              : mode === 'recent' ? 'Recent facts'
              :                     'No retrieval'
  return <span className={cls}>{label}</span>
}

// ─── Decide ───────────────────────────────────────────────────────────────────
function DecideTab() {
  const [situation, setSituation] = useState('')
  const [optionsText, setOptionsText] = useState('')
  const { poll, result, error, loading, reset } = useTaskPoller()

  async function submit(e) {
    e.preventDefault()
    reset()
    const options = optionsText
      ? optionsText.split('\n').map((o) => o.trim()).filter(Boolean)
      : undefined
    const { data } = await client.post('/brain/reason/decide', { situation, options })
    poll(data.task_id)
  }

  return (
    <div className="max-w-2xl space-y-4">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Situation</label>
          <textarea
            className="input w-full h-24 resize-none"
            placeholder="Describe the situation that requires a decision..."
            value={situation}
            onChange={(e) => setSituation(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label">Options (optional — one per line)</label>
          <textarea
            className="input w-full h-20 resize-none"
            placeholder="Option A&#10;Option B&#10;Option C"
            value={optionsText}
            onChange={(e) => setOptionsText(e.target.value)}
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? <SpinnerBtn>Deciding...</SpinnerBtn> : 'Get Decision'}
        </button>
      </form>

      {loading && <ThinkingCard />}

      {result && (
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Decision</p>
            <ConfidenceBadge value={result.confidence} />
          </div>
          <p className="text-slate-100 font-semibold text-base">{result.decision}</p>
          <div>
            <p className="text-xs text-slate-500 mb-1">Reasoning</p>
            <p className="text-slate-300 text-sm leading-relaxed">{result.reasoning}</p>
          </div>
          {result.risks?.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Risks</p>
              <ul className="list-disc list-inside space-y-1">
                {result.risks.map((r, i) => (
                  <li key={i} className="text-slate-300 text-sm">{r}</li>
                ))}
              </ul>
            </div>
          )}
          {result.expected_outcome && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Expected Outcome</p>
              <p className="text-slate-300 text-sm">{result.expected_outcome}</p>
            </div>
          )}
          {result.follow_up_actions?.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Follow-up Actions</p>
              <ul className="list-disc list-inside space-y-1">
                {result.follow_up_actions.map((a, i) => (
                  <li key={i} className="text-slate-300 text-sm">{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {error && <ErrorCard>{error}</ErrorCard>}
    </div>
  )
}

// ─── Lead Analysis ────────────────────────────────────────────────────────────
function LeadTab() {
  const [form, setForm] = useState({ name: '', email: '', phone: '', income: '', credit_score: '' })
  const { poll, result, error, loading, reset } = useTaskPoller()

  function onChange(field) {
    return (e) => setForm((p) => ({ ...p, [field]: e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    reset()
    const lead = {
      name: form.name,
      email: form.email,
      phone: form.phone,
      income: form.income ? parseFloat(form.income) : undefined,
      credit_score: form.credit_score ? parseFloat(form.credit_score) : undefined,
    }
    const { data } = await client.post('/brain/reason/lead', { lead })
    poll(data.task_id)
  }

  return (
    <div className="max-w-2xl space-y-4">
      <form onSubmit={submit} className="grid grid-cols-2 gap-3">
        <div className="col-span-2 sm:col-span-1">
          <label className="label">Full Name</label>
          <input className="input w-full" placeholder="Ahmed Al Rashidi" value={form.name} onChange={onChange('name')} required />
        </div>
        <div className="col-span-2 sm:col-span-1">
          <label className="label">Email</label>
          <input className="input w-full" type="email" placeholder="ahmed@example.com" value={form.email} onChange={onChange('email')} />
        </div>
        <div className="col-span-2 sm:col-span-1">
          <label className="label">Phone</label>
          <input className="input w-full" placeholder="+971 50 000 0000" value={form.phone} onChange={onChange('phone')} />
        </div>
        <div className="col-span-2 sm:col-span-1">
          <label className="label">Monthly Income (AED)</label>
          <input className="input w-full" type="number" placeholder="15000" value={form.income} onChange={onChange('income')} />
        </div>
        <div className="col-span-2 sm:col-span-1">
          <label className="label">Credit Score</label>
          <input className="input w-full" type="number" placeholder="720" value={form.credit_score} onChange={onChange('credit_score')} />
        </div>
        <div className="col-span-2">
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? <SpinnerBtn>Analysing...</SpinnerBtn> : 'Analyse Lead'}
          </button>
        </div>
      </form>

      {loading && <ThinkingCard />}

      {result && (
        <div className="card space-y-4">
          {/* Score + Priority header */}
          <div className="flex items-center gap-4">
            <div className="text-center">
              <p className="text-3xl font-bold text-brand-400">{result.score}</p>
              <p className="text-xs text-slate-500">Score</p>
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex gap-2 flex-wrap">
                <PriorityBadge value={result.priority} />
                <EligibilityBadge value={result.eligibility} />
              </div>
              {result.next_action && (
                <p className="text-sm text-slate-300">
                  <span className="text-slate-500">Next: </span>{result.next_action}
                </p>
              )}
            </div>
          </div>

          {result.recommended_products?.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Recommended Products</p>
              <div className="flex flex-wrap gap-2">
                {result.recommended_products.map((p, i) => (
                  <span key={i} className="badge-blue">{p}</span>
                ))}
              </div>
            </div>
          )}

          {result.opportunities?.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Opportunities</p>
              <ul className="list-disc list-inside space-y-1">
                {result.opportunities.map((o, i) => <li key={i} className="text-emerald-400 text-sm">{o}</li>)}
              </ul>
            </div>
          )}

          {result.key_risks?.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Key Risks</p>
              <ul className="list-disc list-inside space-y-1">
                {result.key_risks.map((r, i) => <li key={i} className="text-red-400 text-sm">{r}</li>)}
              </ul>
            </div>
          )}

          {result.reasoning && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Reasoning</p>
              <p className="text-slate-300 text-sm leading-relaxed">{result.reasoning}</p>
            </div>
          )}
        </div>
      )}

      {error && <ErrorCard>{error}</ErrorCard>}
    </div>
  )
}

// ─── Shared UI Helpers ────────────────────────────────────────────────────────
function ThinkingCard() {
  return (
    <div className="card flex items-center gap-3 text-slate-400">
      <svg className="w-5 h-5 animate-spin text-brand-400" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      <span className="text-sm">Brain is thinking...</span>
    </div>
  )
}

function ErrorCard({ children }) {
  return (
    <div className="rounded-lg bg-red-950/50 border border-red-800 px-4 py-3 text-sm text-red-400">
      {children}
    </div>
  )
}

function SpinnerBtn({ children }) {
  return (
    <span className="flex items-center gap-2">
      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      {children}
    </span>
  )
}

function ConfidenceBadge({ value }) {
  if (value == null) return null
  const pct = Math.round(value * 100)
  const cls = pct >= 70 ? 'badge-green' : pct >= 40 ? 'badge-yellow' : 'badge-red'
  return <span className={cls}>{pct}% confidence</span>
}

function PriorityBadge({ value }) {
  const map = { urgent: 'badge-red', high: 'badge-yellow', medium: 'badge-blue', low: 'badge-green' }
  return <span className={map[value] || 'badge-blue'}>{value}</span>
}

function EligibilityBadge({ value }) {
  if (!value) return null
  const map = {
    likely_eligible: 'badge-green',
    borderline: 'badge-yellow',
    likely_rejected: 'badge-red',
  }
  return <span className={map[value] || 'badge-blue'}>{value?.replace(/_/g, ' ')}</span>
}
