import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Streaming Ask hook — wraps the new `POST /brain/reason/ask/stream` SSE endpoint.
 *
 * Why fetch+ReadableStream instead of EventSource?
 *   • EventSource cannot send a request body (we need the question payload).
 *   • EventSource cannot attach a Bearer token header.
 * The Fetch streaming approach gives us both, while still parsing the SSE
 * wire format manually (event: <type>\ndata: <json>\n\n).
 *
 * On any transport-level failure the hook automatically falls back to the
 * polled `/brain/reason/ask` flow so the user always gets an answer.
 */
const API_BASE = 'http://localhost:9000/api/v1'

export default function useAskStream({ onError } = {}) {
  const [answer, setAnswer]         = useState('')
  const [meta, setMeta]             = useState(null)   // { retrieval_mode, citations[] }
  const [streaming, setStreaming]   = useState(false)
  const [error, setError]           = useState(null)
  const abortRef                    = useRef(null)

  const reset = useCallback(() => {
    setAnswer('')
    setMeta(null)
    setError(null)
  }, [])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
  }, [])

  // Cancel any in-flight stream when the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), [])

  const ask = useCallback(async (question) => {
    if (!question?.trim()) return
    reset()
    setStreaming(true)
    const controller = new AbortController()
    abortRef.current = controller
    const token = localStorage.getItem('access_token')

    try {
      const resp = await fetch(`${API_BASE}/brain/reason/ask/stream`, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ question }),
      })

      if (!resp.ok || !resp.body) {
        throw new Error(`stream rejected: HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      // SSE frames are separated by a blank line (\n\n).
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) !== -1) {
          const frame = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          const evMatch = frame.match(/^event: (.+)$/m)
          const dataMatch = frame.match(/^data: (.+)$/m)
          if (!evMatch || !dataMatch) continue
          const evt = evMatch[1].trim()
          let payload
          try { payload = JSON.parse(dataMatch[1]) } catch { payload = null }
          if (evt === 'meta' && payload) {
            setMeta(payload)
          } else if (evt === 'token' && typeof payload === 'string') {
            setAnswer((a) => a + payload)
          } else if (evt === 'done') {
            setStreaming(false)
          }
        }
      }
      setStreaming(false)
    } catch (e) {
      if (e.name === 'AbortError') {
        // User-initiated stop; not an error.
        return
      }
      setError(e.message || String(e))
      setStreaming(false)
      onError?.(e)
    } finally {
      abortRef.current = null
    }
  }, [onError, reset])

  return { ask, stop, reset, answer, meta, streaming, error }
}
