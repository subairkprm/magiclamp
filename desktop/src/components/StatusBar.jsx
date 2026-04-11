import { useEffect, useState } from 'react'

export default function StatusBar() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('http://localhost:9000/health', { signal: AbortSignal.timeout(3000) })
        setStatus(res.ok ? 'running' : 'error')
      } catch {
        // Fallback to IPC if electronAPI is available
        if (window.electronAPI) {
          const s = await window.electronAPI.getBackendStatus()
          setStatus(s || 'stopped')
        } else {
          setStatus('offline')
        }
      }
    }

    check()
    const interval = setInterval(check, 6000)
    return () => clearInterval(interval)
  }, [])

  const variants = {
    running:  { dot: 'bg-emerald-400 animate-pulse', text: 'text-emerald-400', label: 'Backend Running' },
    starting: { dot: 'bg-yellow-400 animate-pulse',  text: 'text-yellow-400',  label: 'Starting...' },
    checking: { dot: 'bg-slate-400 animate-pulse',   text: 'text-slate-400',   label: 'Checking...' },
    stopped:  { dot: 'bg-red-400',                   text: 'text-red-400',     label: 'Backend Stopped' },
    error:    { dot: 'bg-red-400',                   text: 'text-red-400',     label: 'Backend Error' },
    offline:  { dot: 'bg-red-400',                   text: 'text-red-400',     label: 'Offline' },
  }

  const v = variants[status] || variants.offline

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${v.dot}`} />
      <span className={`text-xs font-medium ${v.text}`}>{v.label}</span>
    </div>
  )
}
