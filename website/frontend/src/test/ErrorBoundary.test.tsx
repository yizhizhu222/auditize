import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from '../components/ErrorBoundary'

const ThrowError = () => {
  throw new Error('Test error message')
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Safe content</div>
      </ErrorBoundary>
    )
    expect(screen.getByTestId('child')).toHaveTextContent('Safe content')
  })

  it('renders fallback when child throws', () => {
    // Suppress console.error for this expected error
    vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('Test error message')).toBeInTheDocument()
    expect(screen.getByText('Retry')).toBeInTheDocument()

    vi.restoreAllMocks()
  })

  it('renders custom fallback when provided', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary fallback={<div data-testid="custom">自定义错误页</div>}>
        <ThrowError />
      </ErrorBoundary>
    )

    expect(screen.getByTestId('custom')).toHaveTextContent('自定义错误页')
    vi.restoreAllMocks()
  })
})
