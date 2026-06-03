import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Login from '../components/Login'
import { LanguageProvider } from '../context/LanguageContext'

function renderWithProviders(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('Login', () => {
  it('renders login form with title', () => {
    renderWithProviders(<Login />)
    expect(screen.getByText('Truffle AI')).toBeInTheDocument()
  })

  it('shows login button disabled initially', () => {
    renderWithProviders(<Login />)
    const button = screen.getByText('Sign In')
    expect(button).toBeDisabled()
  })

  it('has username and password inputs in default mode', () => {
    renderWithProviders(<Login />)
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
  })

  it('switches to TOTP mode', () => {
    renderWithProviders(<Login />)
    fireEvent.click(screen.getByText('TOTP Code'))
    expect(screen.getByText('TOTP Code')).toBeInTheDocument()
  })

  it('calls onLoginSuccess after successful password login', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'test-token', role: 'user' }),
    })
    const onSuccess = vi.fn()
    renderWithProviders(<Login onLoginSuccess={onSuccess} />)
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'testuser' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'password' } })
    const form = document.querySelector('form')!
    fireEvent.submit(form)
    await waitFor(() => {
      expect(localStorage.getItem('nexus-auth-token')).toBe('test-token')
    })
  })

  it('has a register link', () => {
    renderWithProviders(<Login />)
    expect(screen.getByText('No account?')).toBeInTheDocument()
  })

  it('switches to register mode when clicking register', () => {
    renderWithProviders(<Login />)
    fireEvent.click(screen.getByText('Register'))
    expect(screen.getAllByText('Create Account').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Already have an account?')).toBeInTheDocument()
  })
})
