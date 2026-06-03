import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, info: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
    this.props.onError?.(error, info)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div
          className="flex-1 flex flex-col items-center justify-center min-h-0 p-8 text-center"
          style={{ backgroundColor: 'var(--color-bg)' }}
        >
          <svg className="w-14 h-14 mb-4" style={{ color: 'var(--color-text-dim)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
          <h3 className="text-base font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
            Something went wrong
          </h3>
          <p className="text-sm mb-4 max-w-md" style={{ color: 'var(--color-text-muted)' }}>
            {this.state.error?.message || 'An unknown error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-5 py-2 rounded-lg text-sm font-semibold text-white transition-colors"
            style={{ backgroundColor: '#0969DA' }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#0550AE' }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#0969DA' }}
          >
            Retry
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
