import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act, fireEvent, renderHook } from '@testing-library/react'
import { ToastProvider, useToast } from '../context/ToastContext'

describe('ToastContext', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('renders children correctly', () => {
    render(
      <ToastProvider>
        <div data-testid="child">Hello</div>
      </ToastProvider>
    )
    expect(screen.getByTestId('child')).toHaveTextContent('Hello')
  })

  it('shows a toast and auto-dismisses after 2500ms', () => {
    function TestComp() {
      const { showToast } = useToast()
      return <button onClick={() => showToast('Test message')}>Show</button>
    }
    render(
      <ToastProvider>
        <TestComp />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Show'))
    expect(screen.getByText('Test message')).toBeInTheDocument()

    act(() => { vi.advanceTimersByTime(2600) })
    expect(screen.queryByText('Test message')).not.toBeInTheDocument()
  })

  it('shows success toast with checkmark icon', () => {
    function TestComp() {
      const { showToast } = useToast()
      return <button onClick={() => showToast('Saved!', 'success')}>Show</button>
    }
    render(
      <ToastProvider>
        <TestComp />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Show'))
    expect(screen.getByText('Saved!')).toBeInTheDocument()
  })

  it('shows error toast', () => {
    function TestComp() {
      const { showToast } = useToast()
      return <button onClick={() => showToast('Error!', 'error')}>Show</button>
    }
    render(
      <ToastProvider>
        <TestComp />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Show'))
    expect(screen.getByText('Error!')).toBeInTheDocument()
  })

  it('shows info toast', () => {
    function TestComp() {
      const { showToast } = useToast()
      return <button onClick={() => showToast('Info!', 'info')}>Show</button>
    }
    render(
      <ToastProvider>
        <TestComp />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Show'))
    expect(screen.getByText('Info!')).toBeInTheDocument()
  })

  it('dismisses toast on click', () => {
    function TestComp() {
      const { showToast } = useToast()
      return <button onClick={() => showToast('Click dismiss')}>Show</button>
    }
    render(
      <ToastProvider>
        <TestComp />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Show'))
    fireEvent.click(screen.getByText('Click dismiss'))
    expect(screen.queryByText('Click dismiss')).not.toBeInTheDocument()
  })

  it('throws error when useToast used outside provider', () => {
    expect(() => renderHook(() => useToast())).toThrow(
      'useToast must be used within ToastProvider'
    )
  })
})


