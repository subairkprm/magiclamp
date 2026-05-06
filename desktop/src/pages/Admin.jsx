import { useState, useEffect, useCallback } from 'react'
import client from '../api/client'

const TABS = ['Health', 'AI Provider', 'Organizations', 'Users', 'Audit Log']

export default function Admin() {
  const [tab, setTab] = useState('Health')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-100">Admin Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Platform management and monitoring</p>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
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

      {tab === 'Health' && <HealthTab />}
      {tab === 'AI Provider' && <LLMTab />}
      {tab === 'Organizations' && <OrgsTab />}
      {tab === 'Users' && <UsersTab />}
      {tab === 'Audit Log' && <AuditTab />}
    </div>
  )
}

// ─── Health ───────────────────────────────────────────────────────────────────
function HealthTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    client.get('/admin/health')
      .then(({ data }) => setData(data))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const circuitColor = (state) => ({
    closed: 'badge-green',
    open: 'badge-red',
    half_open: 'badge-yellow',
  }[state] || 'badge-blue')

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex items-center gap-3">
        {data && (
          <span className={data.status === 'healthy' ? 'badge-green' : 'badge-red'}>
            {data.status}
          </span>
        )}
        <button onClick={load} disabled={loading} className="btn-secondary text-sm">
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {loading && <p className="text-slate-500 text-sm">Loading health data...</p>}

      {data && (
        <>
          {/* Circuit Breakers */}
          <div className="card">
            <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">Circuit Breakers</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(data.circuits || {}).map(([name, state]) => (
                <div key={name} className="bg-slate-800/50 rounded-lg p-3 text-center">
                  <p className="text-slate-300 text-sm capitalize mb-1">{name}</p>
                  <span className={circuitColor(state)}>{state}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Modules */}
          {data.modules?.length > 0 && (
            <div className="card">
              <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">Modules</p>
              <div className="space-y-2">
                {data.modules.map((m) => (
                  <div key={m.name} className="flex items-center justify-between py-1.5 border-b border-slate-800/50 last:border-0">
                    <span className="text-slate-300 text-sm">{m.name}</span>
                    <div className="flex items-center gap-3">
                      {m.version && <span className="text-xs text-slate-600">{m.version}</span>}
                      <span className={m.health ? 'badge-green' : 'badge-red'}>
                        {m.health ? 'healthy' : 'down'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bus */}
          {data.bus && (
            <div className="card">
              <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">Event Bus</p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {Object.entries(data.bus).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="text-slate-300 font-mono">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ─── AI Provider ──────────────────────────────────────────────────────────────
// Lets the operator pick the active LLM provider, override the model name, and
// validate connectivity end-to-end. API keys themselves stay in env vars
// (server side) — this panel only changes the *selection*.
function LLMTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    client.get('/admin/llm/providers')
      .then(({ data }) => {
        setData(data)
        setProvider(data?.active || '')
        const activeRow = (data?.providers || []).find((p) => p.name === data?.active)
        setModel(activeRow?.model || '')
      })
      .catch(() => setError('Failed to load providers'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  async function save() {
    setSaving(true)
    setError('')
    try {
      await client.put('/admin/llm/active', { provider, model })
      load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function runTest() {
    setTesting(true)
    setTestResult(null)
    try {
      const { data } = await client.post('/admin/llm/test', { provider })
      setTestResult(data)
    } catch (err) {
      setTestResult({ ok: false, error: err.response?.data?.message || 'Request failed' })
    } finally {
      setTesting(false)
    }
  }

  if (loading) return <div className="card text-slate-500 text-sm">Loading providers…</div>

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="card">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">
          Active provider
        </p>
        <p className="text-sm text-slate-400 mb-4">
          MagicLamp talks to one LLM provider at a time. Pick which one — and
          which model — to route every brain call through. API keys are
          configured via environment variables on the server, never stored in
          the database.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Provider</label>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value)
                const row = (data?.providers || []).find((p) => p.name === e.target.value)
                setModel(row?.model || '')
              }}
              className="input w-full"
            >
              {(data?.providers || []).map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}{p.configured ? '' : ' (not configured)'}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Model</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. gpt-4o-mini"
              className="input w-full"
            />
            <p className="text-xs text-slate-600 mt-1">
              Leave blank to use the provider's default model.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={save}
              disabled={saving || !provider}
              className="btn-primary text-sm"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={runTest}
              disabled={testing || !provider}
              className="btn-secondary text-sm"
            >
              {testing ? 'Testing…' : 'Test connection'}
            </button>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          {testResult && (
            <div className={`text-sm rounded p-3 ${testResult.ok ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
              {testResult.ok ? (
                <>
                  <p className="font-mono">✓ {testResult.provider} ({testResult.model})</p>
                  {testResult.response && (
                    <p className="mt-1 text-xs opacity-80">Response: {testResult.response}</p>
                  )}
                </>
              ) : (
                <>
                  <p>✗ Test failed</p>
                  {testResult.error && <p className="mt-1 text-xs opacity-80">{testResult.error}</p>}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">
          Available providers
        </p>
        <div className="space-y-2">
          {(data?.providers || []).map((p) => (
            <div key={p.name} className="flex items-center justify-between text-sm py-2 border-b border-slate-800 last:border-0">
              <div>
                <span className="text-slate-200 font-mono">{p.name}</span>
                {p.active && <span className="ml-2 badge-green text-xs">active</span>}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-500 font-mono text-xs">{p.model}</span>
                <span className={`text-xs ${p.configured ? 'badge-green' : 'badge-yellow'}`}>
                  {p.configured ? 'configured' : 'no key'}
                </span>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-600 mt-3">
          To configure a provider, set its API-key environment variable
          (e.g. <code className="font-mono">OPENAI_API_KEY</code>) on the server and restart.
        </p>
      </div>
    </div>
  )
}

// ─── Organizations ────────────────────────────────────────────────────────────
function OrgsTab() {
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', slug: '', plan: 'free' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    client.get('/admin/orgs')
      .then(({ data }) => setOrgs(data || []))
      .catch(() => setOrgs([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  async function createOrg(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await client.post('/admin/orgs', form)
      setShowCreate(false)
      setForm({ name: '', slug: '', plan: 'free' })
      load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create organization')
    } finally {
      setSaving(false)
    }
  }

  const planColor = { enterprise: 'badge-yellow', professional: 'badge-blue', starter: 'badge-green', free: 'badge-blue' }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary text-sm">
          {showCreate ? 'Cancel' : '+ New Organization'}
        </button>
        <button onClick={load} disabled={loading} className="btn-secondary text-sm">
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {showCreate && (
        <div className="card max-w-md">
          <p className="text-sm font-semibold text-slate-200 mb-3">Create Organization</p>
          <form onSubmit={createOrg} className="space-y-3">
            <div>
              <label className="label">Name</label>
              <input className="input w-full" placeholder="Acme Bank" value={form.name}
                onChange={(e) => setForm(p => ({ ...p, name: e.target.value }))} required />
            </div>
            <div>
              <label className="label">Slug</label>
              <input className="input w-full" placeholder="acme-bank" value={form.slug}
                onChange={(e) => setForm(p => ({ ...p, slug: e.target.value }))} required
                pattern="[a-z0-9\-]+" title="Lowercase letters, numbers, dashes" />
            </div>
            <div>
              <label className="label">Plan</label>
              <select className="input w-full" value={form.plan}
                onChange={(e) => setForm(p => ({ ...p, plan: e.target.value }))}>
                {['free', 'starter', 'professional', 'enterprise'].map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button type="submit" disabled={saving} className="btn-primary text-sm">
              {saving ? 'Creating...' : 'Create'}
            </button>
          </form>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/50">
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Name</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Slug</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Plan</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {orgs.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-600">{loading ? 'Loading...' : 'No organizations'}</td></tr>
            ) : (
              orgs.map((o) => (
                <tr key={o.id} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="px-4 py-3 text-slate-200 font-medium">{o.name}</td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{o.slug}</td>
                  <td className="px-4 py-3"><span className={planColor[o.plan] || 'badge-blue'}>{o.plan}</span></td>
                  <td className="px-4 py-3"><span className={o.is_active ? 'badge-green' : 'badge-red'}>{o.is_active ? 'active' : 'inactive'}</span></td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{o.created_at ? new Date(o.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Users ────────────────────────────────────────────────────────────────────
function UsersTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'user' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    client.get('/admin/users')
      .then(({ data }) => setUsers(data || []))
      .catch(() => setUsers([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  async function createUser(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await client.post('/admin/users', form)
      setShowCreate(false)
      setForm({ username: '', email: '', password: '', role: 'user' })
      load()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create user')
    } finally {
      setSaving(false)
    }
  }

  async function deleteUser(id) {
    if (!confirm('Delete this user?')) return
    setDeleting(id)
    try {
      await client.delete(`/admin/users/${id}`)
      load()
    } catch { /* ignore */ }
    setDeleting(null)
  }

  const roleColor = { super_admin: 'badge-red', admin: 'badge-yellow', agent: 'badge-blue', user: 'badge-green' }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary text-sm">
          {showCreate ? 'Cancel' : '+ New User'}
        </button>
        <button onClick={load} disabled={loading} className="btn-secondary text-sm">
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {showCreate && (
        <div className="card max-w-md">
          <p className="text-sm font-semibold text-slate-200 mb-3">Create User</p>
          <form onSubmit={createUser} className="space-y-3">
            <div>
              <label className="label">Username</label>
              <input className="input w-full" placeholder="john_doe" value={form.username}
                onChange={(e) => setForm(p => ({ ...p, username: e.target.value }))} required />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input w-full" type="email" placeholder="john@example.com" value={form.email}
                onChange={(e) => setForm(p => ({ ...p, email: e.target.value }))} required />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input w-full" type="password" placeholder="Min 8 chars, 1 uppercase, 1 number, 1 special" value={form.password}
                onChange={(e) => setForm(p => ({ ...p, password: e.target.value }))} required />
            </div>
            <div>
              <label className="label">Role</label>
              <select className="input w-full" value={form.role}
                onChange={(e) => setForm(p => ({ ...p, role: e.target.value }))}>
                {['user', 'agent', 'admin', 'super_admin'].map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button type="submit" disabled={saving} className="btn-primary text-sm">
              {saving ? 'Creating...' : 'Create User'}
            </button>
          </form>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/50">
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Name</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Email</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Role</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Created</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-600">{loading ? 'Loading...' : 'No users'}</td></tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="px-4 py-3 text-slate-200">{u.name || u.username || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{u.email}</td>
                  <td className="px-4 py-3"><span className={roleColor[u.role] || 'badge-blue'}>{u.role}</span></td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => deleteUser(u.id)}
                      disabled={deleting === u.id}
                      className="text-xs text-red-500 hover:text-red-400 disabled:opacity-50 transition-colors"
                    >
                      {deleting === u.id ? '...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Audit Log ────────────────────────────────────────────────────────────────
function AuditTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    const params = filter ? { action: filter } : {}
    client.get('/admin/audit-log', { params })
      .then(({ data }) => setLogs(data || []))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [filter])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center gap-3">
        <input
          className="input w-56"
          placeholder="Filter by action..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <button onClick={load} disabled={loading} className="btn-secondary text-sm">
          {loading ? 'Loading...' : 'Search'}
        </button>
        {logs.length > 0 && <span className="text-xs text-slate-500">{logs.length} entries</span>}
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/50">
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Action</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Resource</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">User</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">IP</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-600">{loading ? 'Loading...' : 'No audit logs'}</td></tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-brand-400">{log.action}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {log.resource_type}{log.resource_id ? ` #${String(log.resource_id).slice(0, 8)}` : ''}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{log.user_id ? String(log.user_id).slice(0, 12) + '…' : '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{log.ip_address || '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
