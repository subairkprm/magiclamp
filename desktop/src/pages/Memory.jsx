import { useState, useEffect, useCallback } from 'react'
import client from '../api/client'

export default function Memory() {
  const [tab, setTab] = useState('Store')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-100">Memory Manager</h1>
        <p className="text-slate-500 text-sm mt-1">Store and recall facts with confidence scoring</p>
      </div>

      <div className="flex gap-2 mb-6">
        {['Store', 'Recall', 'All Facts', 'Stats'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`tab-btn ${tab === t ? 'active' : ''}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Store' && <StoreTab />}
      {tab === 'Recall' && <RecallTab />}
      {tab === 'All Facts' && <AllFactsTab />}
      {tab === 'Stats' && <StatsTab />}
    </div>
  )
}

// ─── Store Fact ───────────────────────────────────────────────────────────────
function StoreTab() {
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const [confidence, setConfidence] = useState('0.9')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setSuccess('')
    setError('')
    try {
      await client.post('/brain/memory/remember', {
        key,
        value,
        confidence: parseFloat(confidence),
        source: 'desktop',
      })
      setSuccess(`Fact "${key}" stored successfully.`)
      setKey('')
      setValue('')
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to store fact')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg space-y-4">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Key</label>
          <input
            className="input w-full"
            placeholder="e.g. bank.policy.max_loan_term"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            required
            pattern="[a-z0-9._\-]+"
            title="Lowercase letters, numbers, dots, underscores, dashes"
          />
          <p className="text-xs text-slate-600 mt-1">Lowercase letters, numbers, dots, underscores, dashes only</p>
        </div>
        <div>
          <label className="label">Value</label>
          <textarea
            className="input w-full h-24 resize-none"
            placeholder="The maximum loan term is 25 years..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="label">Confidence (0.0 – 1.0)</label>
          <input
            className="input w-32"
            type="number"
            min="0" max="1" step="0.05"
            value={confidence}
            onChange={(e) => setConfidence(e.target.value)}
          />
        </div>

        {success && (
          <div className="rounded-lg bg-emerald-950/50 border border-emerald-800 px-3 py-2 text-sm text-emerald-400">{success}</div>
        )}
        {error && (
          <div className="rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-sm text-red-400">{error}</div>
        )}

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Storing...' : 'Store Fact'}
        </button>
      </form>
    </div>
  )
}

// ─── Recall ───────────────────────────────────────────────────────────────────
function RecallTab() {
  const [key, setKey] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const { data } = await client.get(`/brain/memory/recall/${encodeURIComponent(key)}`)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg space-y-4">
      <form onSubmit={submit} className="flex gap-2">
        <input
          className="input flex-1"
          placeholder="Enter key to recall..."
          value={key}
          onChange={(e) => setKey(e.target.value)}
          required
        />
        <button type="submit" disabled={loading} className="btn-primary shrink-0">
          {loading ? 'Recalling...' : 'Recall'}
        </button>
      </form>

      {result && (
        <div className="card">
          {result.found ? (
            <>
              <div className="flex items-center gap-2 mb-2">
                <span className="badge-green">Found</span>
                <span className="text-xs text-slate-500 font-mono">{result.key}</span>
              </div>
              <p className="text-slate-200 leading-relaxed whitespace-pre-wrap">
                {typeof result.value === 'object' ? JSON.stringify(result.value, null, 2) : String(result.value)}
              </p>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <span className="badge-red">Not Found</span>
              <span className="text-sm text-slate-400">No fact stored under key "{result.key}"</span>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-950/50 border border-red-800 px-3 py-2 text-sm text-red-400">{error}</div>
      )}
    </div>
  )
}

// ─── All Facts ────────────────────────────────────────────────────────────────
function AllFactsTab() {
  const [facts, setFacts] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await client.get('/brain/memory/facts')
      setFacts(data)
    } catch {
      setFacts({})
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const entries = facts
    ? Object.entries(facts).filter(([k, v]) =>
        !filter || k.includes(filter) || String(v).toLowerCase().includes(filter.toLowerCase())
      )
    : []

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          className="input w-64"
          placeholder="Filter keys..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <button onClick={load} disabled={loading} className="btn-secondary text-sm">
          {loading ? 'Loading...' : 'Refresh'}
        </button>
        {facts && <span className="text-xs text-slate-500">{entries.length} facts</span>}
      </div>

      {loading && <p className="text-slate-500 text-sm">Loading...</p>}

      {facts && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50">
                <th className="text-left px-4 py-3 text-slate-400 font-medium w-1/3">Key</th>
                <th className="text-left px-4 py-3 text-slate-400 font-medium">Value</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-4 py-8 text-center text-slate-600">No facts found</td>
                </tr>
              ) : (
                entries.map(([k, v]) => (
                  <tr key={k} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-brand-400 text-xs break-all">{k}</td>
                    <td className="px-4 py-3 text-slate-300 break-all">
                      {String(v).length > 120 ? String(v).slice(0, 120) + '…' : String(v)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function StatsTab() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    client.get('/brain/memory/stats')
      .then(({ data }) => setStats(data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [])

  const cards = stats ? [
    { label: 'Facts',            value: stats.facts,             color: 'text-brand-400' },
    { label: 'Events',           value: stats.events,            color: 'text-purple-400' },
    { label: 'Training Samples', value: stats.training_samples,  color: 'text-emerald-400' },
    { label: 'Decisions',        value: stats.decisions,         color: 'text-yellow-400' },
  ] : []

  return (
    <div>
      {loading && <p className="text-slate-500 text-sm">Loading stats...</p>}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {cards.map((c) => (
            <div key={c.label} className="card text-center">
              <p className={`text-3xl font-bold ${c.color}`}>{c.value ?? '—'}</p>
              <p className="text-slate-500 text-sm mt-1">{c.label}</p>
            </div>
          ))}
        </div>
      )}
      {!loading && !stats && (
        <p className="text-slate-500 text-sm">Failed to load stats. Is the backend running?</p>
      )}
    </div>
  )
}
