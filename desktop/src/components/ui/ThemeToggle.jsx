import { useEffect, useState, useCallback } from 'react'

const STORAGE_KEY = 'ml.theme'         // 'light' | 'dark' | 'system'
const DIR_STORAGE_KEY = 'ml.dir'       // 'ltr' | 'rtl'

function applyTheme(mode) {
  const root = document.documentElement
  root.classList.remove('theme-light', 'theme-dark')
  if (mode === 'light') root.classList.add('theme-light')
  if (mode === 'dark')  root.classList.add('theme-dark')
}

function applyDir(dir) {
  document.documentElement.dir = dir
  document.documentElement.classList.toggle('dir-rtl', dir === 'rtl')
}

/**
 * Theme + direction toggle. The chosen values persist to localStorage and
 * are applied immediately on mount so the very first paint is correct.
 *
 * Direction (LTR/RTL) is exposed because MagicLamp targets UAE banking and
 * Arabic right-to-left support is a hard requirement.
 */
export default function ThemeToggle({ compact = false }) {
  const [mode, setMode] = useState('system')
  const [dir, setDir] = useState('ltr')

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) || 'system'
    const savedDir = localStorage.getItem(DIR_STORAGE_KEY) || 'ltr'
    setMode(saved)
    setDir(savedDir)
    applyTheme(saved)
    applyDir(savedDir)
  }, [])

  const cycle = useCallback(() => {
    const next = mode === 'system' ? 'light' : mode === 'light' ? 'dark' : 'system'
    setMode(next)
    localStorage.setItem(STORAGE_KEY, next)
    applyTheme(next)
  }, [mode])

  const toggleDir = useCallback(() => {
    const next = dir === 'ltr' ? 'rtl' : 'ltr'
    setDir(next)
    localStorage.setItem(DIR_STORAGE_KEY, next)
    applyDir(next)
  }, [dir])

  const icon = mode === 'system' ? '🖥' : mode === 'light' ? '☀️' : '🌙'

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={cycle}
        title={`Theme: ${mode} (click to change)`}
        aria-label={`Switch theme — current: ${mode}`}
        className="px-2 py-1 rounded-md text-fg-muted hover:text-fg hover:bg-elevated transition-colors text-sm"
      >
        <span aria-hidden="true">{icon}</span>
        {!compact && <span className="ml-1">{mode}</span>}
      </button>
      <button
        type="button"
        onClick={toggleDir}
        title={`Direction: ${dir.toUpperCase()} (click to flip)`}
        aria-label={`Switch direction — current: ${dir.toUpperCase()}`}
        className="px-2 py-1 rounded-md text-fg-muted hover:text-fg hover:bg-elevated transition-colors text-xs font-mono"
      >
        {dir === 'ltr' ? 'A→' : '←ا'}
      </button>
    </div>
  )
}
