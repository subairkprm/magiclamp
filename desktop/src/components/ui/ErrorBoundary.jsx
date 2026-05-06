import { Component } from 'react'

/**
 * App-level error boundary so a render-time crash in any page surfaces a
 * usable recovery UI instead of a white screen. Logs the error to the
 * console for the bundled DevTools and to a no-op `onError` prop so callers
 * can wire telemetry later.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('UI ErrorBoundary caught:', error, info)
    this.props.onError?.(error, info)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div role="alert" className="p-6 max-w-xl mx-auto mt-12 card">
        <h2 className="text-lg font-semibold text-fg mb-2">Something went wrong</h2>
        <p className="text-sm text-fg-muted mb-4">
          The MagicLamp UI ran into an unexpected error. You can try again, or
          reload the app.
        </p>
        <pre className="text-xs whitespace-pre-wrap text-red-400 mb-4 max-h-40 overflow-auto">
          {String(this.state.error)}
        </pre>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={this.reset}>Try again</button>
          <button className="btn-primary" onClick={() => window.location.reload()}>Reload app</button>
        </div>
      </div>
    )
  }
}
