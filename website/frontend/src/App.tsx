import { useState, useEffect } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import AdminPage from './components/AdminPage'
import LandingPage from './components/LandingPage'
import { LanguageProvider } from './context/LanguageContext'
import { apiFetch } from './lib/api'

const IS_ADMIN_PORT = window.location.port === '8002'

function usePath() {
  const [path, setPath] = useState(window.location.pathname)
  useEffect(() => {
    const handler = () => setPath(window.location.pathname)
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])
  return path
}

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [authLoading, setAuthLoading] = useState(true)
  const path = usePath()

  // On mount, check for existing JWT and auto-login if valid
  useEffect(() => {
    const token = localStorage.getItem('nexus-auth-token')

    // ── PWA: listen for service worker updates and reload ──
    if ('serviceWorker' in navigator) {
      // Check for SW updates every time the page loads
      navigator.serviceWorker.getRegistration().then(reg => {
        if (reg) {
          reg.addEventListener('updatefound', () => {
            const newSW = reg.installing
            if (newSW) {
              newSW.addEventListener('statechange', () => {
                // New SW activated → reload to get fresh content
                if (newSW.state === 'activated') {
                  window.location.reload()
                }
              })
            }
          })
        }
      })
      // Also re-check on page focus (user comes back to tab)
      let checking = false
      window.addEventListener('focus', () => {
        if (!checking) {
          checking = true
          navigator.serviceWorker.getRegistration().then(reg => {
            if (reg) reg.update()
          }).finally(() => { checking = false })
        }
      })
    }

    // Admin port: auto-login with admin backend (no password needed)
    if (IS_ADMIN_PORT) {
      const doAutoLogin = async () => {
        try {
          const { data } = await apiFetch('/api/v1/admin/auto-login')
          localStorage.setItem('nexus-auth-token', data.access_token)
          localStorage.setItem('nexus-auth-role', data.role || 'admin')
          setIsLoggedIn(true)
        } catch {
          // Ignore — show login page if auto-login fails
        }
        setAuthLoading(false)
      }
      doAutoLogin()
      return
    }

    // Normal port: check existing JWT
    if (!token) {
      setAuthLoading(false)
      return
    }
    apiFetch('/api/v1/auth/verify', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(({ data }) => {
        setIsLoggedIn(true)
        if (data.user?.role) localStorage.setItem('nexus-auth-role', data.user.role)
      })
      .catch(() => {
        localStorage.removeItem('nexus-auth-token')
        localStorage.removeItem('nexus-auth-role')
      })
      .finally(() => setAuthLoading(false))
  }, [])

  const handleLoginSuccess = () => {
    setIsLoggedIn(true)
  }

  const navigateToLogin = () => {
    window.location.pathname = '/login'
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0D1117]">
        <div className="w-6 h-6 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
      </div>
    )
  }

  if (isLoggedIn) {
    // Admin port: render AdminPage directly (no sidebar, no landing page)
    if (IS_ADMIN_PORT) {
      return (
        <LanguageProvider>
          <AdminPage />
        </LanguageProvider>
      )
    }
    return (
      <LanguageProvider>
        <Dashboard />
      </LanguageProvider>
    )
  }

  // Not logged in — show landing page at /, login form at /login
  return (
    <LanguageProvider>
      {path === '/login' ? (
        <Login onLoginSuccess={handleLoginSuccess} />
      ) : (
        <LandingPage />
      )}
    </LanguageProvider>
  )
}
