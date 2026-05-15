import { useState, useRef } from 'react'
import client from '../api/client'

/**
 * useTaskPoller — polls GET /brain/tasks/{taskId} until status is completed/failed.
 * Returns { poll, result, error, loading }
 */
export function useTaskPoller() {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef(null)

  function poll(taskId, onDone) {
    setLoading(true)
    setResult(null)
    setError(null)

    let attempts = 0
    const MAX_ATTEMPTS = 40
    const BASE_DELAY = 1500

    function doCheck() {
      client.get(`/brain/tasks/${taskId}`)
        .then(({ data }) => {
          if (data.status === 'completed') {
            setResult(data.result)
            setLoading(false)
            if (onDone) onDone(data.result, null)
          } else if (data.status === 'failed') {
            const err = data.error || 'Task failed'
            setError(err)
            setLoading(false)
            if (onDone) onDone(null, err)
          } else {
            attempts++
            if (attempts >= MAX_ATTEMPTS) {
              setError('Timed out waiting for response')
              setLoading(false)
            } else {
              const delay = Math.min(BASE_DELAY * Math.pow(1.2, attempts), 8000)
              timerRef.current = setTimeout(doCheck, delay)
            }
          }
        })
        .catch((err) => {
          setError(err.response?.data?.message || err.message || 'Request failed')
          setLoading(false)
        })
    }

    doCheck()
  }

  function reset() {
    clearTimeout(timerRef.current)
    setResult(null)
    setError(null)
    setLoading(false)
  }

  return { poll, result, error, loading, reset }
}
