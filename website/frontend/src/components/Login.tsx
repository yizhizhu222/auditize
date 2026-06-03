import { useState, useRef, useMemo, type FormEvent } from 'react'
import PigLogo from './PigLogo'
import { useT } from '../context/LanguageContext'
import { apiFetch } from '../lib/api'

interface LoginProps {
  onLoginSuccess?: () => void
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const { t } = useT()
  const [mode, setMode] = useState<'login' | 'register' | 'verify' | 'setup_totp'>('login')
  const [loginMethod, setLoginMethod] = useState<'password' | 'totp'>('password')
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [digits, setDigits] = useState<string[]>(Array(6).fill(''))
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  const [regUsername, setRegUsername] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regInvite, setRegInvite] = useState('')
  // Registration response data (for TOTP setup display)
  const [totpSecret, setTotpSecret] = useState('')
  const [provisioningUri, setProvisioningUri] = useState('')
  // Email verification state
  const [verifyEmail, setVerifyEmail] = useState('')
  const [verifyCode, setVerifyCode] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [codeCooldown, setCodeCooldown] = useState(0)
  const [verified, setVerified] = useState(false)

  // Computed password validation
  const pwChecks = useMemo(() => ({
    len: regPassword.length >= 8,
    upper: /[A-Z]/.test(regPassword),
    lower: /[a-z]/.test(regPassword),
    digit: /\d/.test(regPassword),
  }), [regPassword])
  const pwValid = pwChecks.len && pwChecks.upper && pwChecks.lower && pwChecks.digit

  const focusInput = (idx: number) => inputRefs.current[idx]?.focus()

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (loginMethod === 'password') {
      if (!loginUsername.trim() || !loginPassword) { setError('Please enter username and password'); return }
    } else {
      if (digits.join('').length !== 6) return
    }
    setLoading(true)
    try {
      const body = loginMethod === 'password'
        ? { username: loginUsername.trim(), password: loginPassword }
        : { token: digits.join('') }
      const { data } = await apiFetch('/api/v1/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      localStorage.setItem('nexus-auth-token', data.access_token)
      if (data.role) localStorage.setItem('nexus-auth-role', data.role)
      setLoading(false)
      onLoginSuccess?.()
    } catch (err: any) {
      setError(err.message || 'Cannot connect to server')
      if (loginMethod === 'totp') setDigits(Array(6).fill(''))
      setLoading(false)
    }
  }

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    if (!regUsername.trim() || !regPassword.trim()) { setError('Please enter username and password'); return }
    setLoading(true)
    setError('')
    try {
      const { data } = await apiFetch('/api/v1/auth/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: regUsername.trim(), password: regPassword, email: regEmail.trim(), invite_code: regInvite.trim() }),
      })
      // Store TOTP info for setup display
      setTotpSecret(data.totp_secret || '')
      setProvisioningUri(data.provisioning_uri || '')
      // If SMTP is configured and email provided, verify email first
      if (data.suggest_verify && regEmail.trim()) {
        setVerifyEmail(regEmail.trim())
        setVerified(false)
        setCodeSent(false)
        setVerifyCode('')
        setLoading(false)
        setMode('verify')
        return
      }
      // Otherwise, show TOTP setup directly
      setLoading(false)
      setMode('setup_totp')
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    }
    setLoading(false)
  }

  const handleSendCode = async () => {
    setError('')
    setLoading(true)
    try {
      await apiFetch('/api/v1/auth/send-verification-code', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyEmail }),
      })
      setCodeSent(true)
      setCodeCooldown(60)
      const timer = setInterval(() => {
        setCodeCooldown(prev => {
          if (prev <= 1) { clearInterval(timer); return 0 }
          return prev - 1
        })
      }, 1000)
    } catch (err: any) {
      setError(err.message || 'Failed to send code')
    }
    setLoading(false)
  }

  const handleVerifyCode = async () => {
    if (verifyCode.length !== 6) return
    setError('')
    setLoading(true)
    try {
      await apiFetch('/api/v1/auth/verify-email', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyEmail, code: verifyCode }),
      })
      setVerified(true)
      setLoading(false)
      setMode('setup_totp')
    } catch (err: any) {
      setError(err.message || 'Email verification failed')
    }
    setLoading(false)
  }

  const switchMode = () => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setDigits(Array(6).fill('')); setTotpSecret(''); setProvisioningUri('') }

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950">
      <div className="absolute inset-0 opacity-50"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='g' width='60' height='60' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 60 0 L 0 0 0 60' fill='none' stroke='rgba(55,65,81,0.15)' stroke-width='1'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='100%25' height='100%25' fill='url(%23g)'/%3E%3C/svg%3E")` }} />
      <form onSubmit={(e) => { if (mode === 'login') handleLogin(e); else if (mode === 'register') handleRegister(e); e.preventDefault(); }} className="relative z-10 w-full max-w-md mx-4">
        <a href="/" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-4 ml-1 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" /></svg>
          Back to Home
        </a>
        <div className="bg-slate-800/80 backdrop-blur-xl border border-slate-700/60 rounded-2xl shadow-2xl shadow-black/50 p-10">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 flex items-center justify-center">
              <PigLogo size={56} />
            </div>
          </div>
          <h1 className="text-center text-2xl font-bold mb-1" style={{ color: '#F472B6' }}>
            {t('login.title')}
          </h1>
          <p className="text-center text-xs mb-6" style={{ color: 'var(--color-text-dim)' }}>
            {t('login.subtitle')}
          </p>

          {mode === 'login' ? (
            <>
              <div className="flex justify-center gap-4 mb-6">
                <button type="button" onClick={() => { setLoginMethod('password'); setError('') }}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${loginMethod === 'password' ? 'text-pink-400 bg-pink-400/10' : 'text-slate-500 hover:text-slate-300'}`}>
                  Password Login
                </button>
                <button type="button" onClick={() => { setLoginMethod('totp'); setError(''); setDigits(Array(6).fill('')) }}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${loginMethod === 'totp' ? 'text-pink-400 bg-pink-400/10' : 'text-slate-500 hover:text-slate-300'}`}>
                  {t('login.totpLogin')}
                </button>
              </div>
              {loginMethod === 'password' ? (
                <div className="space-y-4 mb-6">
                  <input type="text" value={loginUsername} onChange={e => setLoginUsername(e.target.value)}
                    placeholder="Username" autoFocus
                    className="w-full px-4 py-3 rounded-lg bg-slate-900/80 border border-slate-600 text-white text-sm focus:outline-none focus:border-pink-400 transition-all" />
                  <input type="password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)}
                    placeholder="Password"
                    className="w-full px-4 py-3 rounded-lg bg-slate-900/80 border border-slate-600 text-white text-sm focus:outline-none focus:border-pink-400 transition-all" />
                  {error && <p className="text-center text-red-400 text-xs">{error}</p>}
                </div>
              ) : (
                <div className="mb-6">
                  <div className="flex items-center justify-center gap-3">
                    {digits.map((digit, idx) => (
                      <input key={idx} ref={(el) => { inputRefs.current[idx] = el }}
                        type="text" inputMode="numeric" maxLength={1} value={digit}
                        onChange={(e) => {
                          const d = e.target.value.replace(/\D/g, '').slice(-1)
                          const next = [...digits]; next[idx] = d; setDigits(next)
                          if (d && idx < 5) focusInput(idx + 1); setError('')
                        }}
                        onKeyDown={(e) => { if (e.key === 'Backspace' && !digits[idx] && idx > 0) focusInput(idx - 1) }}
                        className="w-12 h-14 text-center text-xl font-mono font-bold text-white bg-slate-900/80 border border-slate-600 rounded-lg focus:outline-none focus:border-pink-400 focus:ring-2 focus:ring-pink-400/30" />
                    ))}
                  </div>
                  {error && <p className="text-center text-red-400 text-xs mt-3">{error}</p>}
                </div>
              )}
              <button type="submit" disabled={loading || (loginMethod === 'password' ? (!loginUsername.trim() || !loginPassword) : digits.join('').length !== 6)}
                className="w-full py-3 px-6 rounded-lg bg-blue-500 text-white font-semibold text-base transition-all duration-300 hover:bg-blue-400 disabled:opacity-40 disabled:cursor-not-allowed">
                {loading ? t('login.verifying') : t('login.signIn')}
              </button>
            </>
          ) : mode === 'register' ? (
            <>
              <p className="text-center text-slate-400 text-sm mb-6">{t('login.createAccount')}</p>
              <div className="space-y-4 mb-6">
                <input type="text" value={regUsername} onChange={e => setRegUsername(e.target.value)}
                  placeholder={t('login.username')} autoFocus
                  className="w-full px-4 py-3 rounded-lg bg-slate-900/80 border border-slate-600 text-white text-sm focus:outline-none focus:border-pink-400 transition-all" />
                <input type="email" value={regEmail} onChange={e => setRegEmail(e.target.value)}
                  placeholder={t('login.email')}
                  className="w-full px-4 py-3 rounded-lg bg-slate-900/80 border border-slate-600 text-white text-sm focus:outline-none focus:border-pink-400 transition-all" />
                <input type="text" value={regInvite} onChange={e => setRegInvite(e.target.value)}
                  placeholder={t('login.inviteCode')}
                  className="w-full px-4 py-3 rounded-lg bg-slate-900/80 border border-slate-600 text-white text-sm focus:outline-none focus:border-pink-400 transition-all" />
                <input type="password" value={regPassword} onChange={e => setRegPassword(e.target.value)}
                  placeholder={t('login.password')}
                  className="w-full px-4 py-3 rounded-lg bg-slate-900/80 border border-slate-600 text-white text-sm focus:outline-none focus:border-pink-400 transition-all" />
                <div className="text-xs space-y-1 mt-2 px-1">
                  <p className="text-amber-400 font-medium mb-1">Password must contain:</p>
                  <div className={pwChecks.len ? 'text-green-400' : 'text-slate-400'}>{pwChecks.len ? '✓' : '○'} At least 8 characters</div>
                  <div className={pwChecks.upper ? 'text-green-400' : 'text-slate-400'}>{pwChecks.upper ? '✓' : '○'} An uppercase letter (A-Z)</div>
                  <div className={pwChecks.lower ? 'text-green-400' : 'text-slate-400'}>{pwChecks.lower ? '✓' : '○'} A lowercase letter (a-z)</div>
                  <div className={pwChecks.digit ? 'text-green-400' : 'text-slate-400'}>{pwChecks.digit ? '✓' : '○'} A digit (0-9)</div>
                </div>
                {error && <p className="text-center text-red-400 text-xs">{error}</p>}
              </div>
              <button type="submit" disabled={loading || !regUsername.trim() || !pwValid}
                className="w-full py-3 px-6 rounded-lg bg-blue-500 text-white font-semibold text-base transition-all duration-300 hover:bg-blue-400 disabled:opacity-40 disabled:cursor-not-allowed"
                title={!pwValid && regPassword ? 'Password requirements not met (see above)' : !regUsername.trim() ? 'Enter a username first' : ''}>
                {loading ? t('login.creatingAccount') : t('login.createAccount')}
              </button>
              {!loading && (!regUsername.trim() || !pwValid) && (
                <p className="text-center text-amber-400 text-xs mt-3">
                  {!regUsername.trim()
                    ? 'Enter a username to continue'
                    : 'Complete all password requirements above (8+ chars, upper + lower + digit)'}
                </p>
              )}
            </>
          ) : mode === 'verify' ? (
            <>
              <p className="text-center text-slate-400 text-sm mb-2">{t('login.verifyEmail')}</p>
              <p className="text-center text-slate-500 text-xs mb-6">
                {verified
                  ? t('login.emailVerified')
                  : `Code sent to ${verifyEmail}`}
              </p>
              {!codeSent && (
                <div className="flex justify-center mb-4">
                  <button type="button" onClick={handleSendCode} disabled={loading}
                    className="px-6 py-2.5 rounded-lg bg-blue-500 text-white font-semibold text-sm transition-all hover:bg-blue-400 disabled:opacity-40">
                    {loading ? t('login.sending') : t('login.sendCode')}
                  </button>
                </div>
              )}
              {codeSent && !verified && (
                <div className="space-y-4 mb-4">
                  <div className="flex items-center justify-center gap-3">
                    {Array(6).fill(0).map((_, idx) => (
                      <input key={idx} type="text" inputMode="numeric" maxLength={1}
                        value={verifyCode[idx] || ''}
                        onChange={(e) => {
                          const d = e.target.value.replace(/\D/g, '').slice(-1)
                          const next = [...verifyCode.padEnd(6, ' ')]
                          next[idx] = d || ' '
                          setVerifyCode(next.join('').trim())
                          if (d && idx < 5) {
                            const nextInput = document.getElementById(`vc-${idx + 1}`)
                            nextInput?.focus()
                          }
                        }}
                        id={`vc-${idx}`}
                        className="w-12 h-14 text-center text-xl font-mono font-bold text-white bg-slate-900/80 border border-slate-600 rounded-lg focus:outline-none focus:border-pink-400 focus:ring-2 focus:ring-pink-400/30" />
                    ))}
                  </div>
                  {error && <p className="text-center text-red-400 text-xs">{error}</p>}
                  <button type="button" onClick={handleVerifyCode}
                    disabled={loading || verifyCode.length !== 6}
                    className="w-full py-3 px-6 rounded-lg bg-blue-500 text-white font-semibold text-base transition-all hover:bg-blue-400 disabled:opacity-40">
                    {loading ? t('login.verifyingCode') : t('login.verifyCode')}
                  </button>
                  <div className="text-center">
                    <button type="button" onClick={handleSendCode}
                      disabled={loading || codeCooldown > 0}
                      className="text-xs text-slate-500 hover:text-slate-300 underline disabled:opacity-40">
                      {codeCooldown > 0 ? `${codeCooldown}${t('login.resendCooldown')}` : t('login.resendCode')}
                    </button>
                  </div>
                </div>
              )}
              {verified && (
                <div className="text-center mb-4">
                  <p className="text-green-400 text-sm mb-3">{t('login.emailVerified')}</p>
                  <button type="button" onClick={() => setMode('setup_totp')}
                    className="px-6 py-2.5 rounded-lg bg-blue-500 text-white font-semibold text-sm transition-all hover:bg-blue-400">
                    {t('login.next')}
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              <p className="text-center text-slate-400 text-sm mb-2">{t('login.setupTotp')}</p>
              <p className="text-center text-slate-500 text-xs mb-6">
                {t('login.setupTotpDesc')}
              </p>
              {provisioningUri && (
                <div className="flex justify-center mb-4">
                  <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(provisioningUri)}`}
                    alt="TOTP QR Code"
                    className="rounded-lg border border-slate-600"
                    style={{ width: 200, height: 200 }} />
                </div>
              )}
              {totpSecret && (
                <div className="mb-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">{t('login.totpSecret')}</p>
                  <code className="text-sm font-mono bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-600 text-pink-300 select-all">
                    {totpSecret}
                  </code>
                </div>
              )}
              <div className="text-center">
                <button type="button"
                  onClick={() => { setMode('login'); setLoginMethod('password'); setLoginUsername(regUsername.trim()) }}
                  className="px-6 py-2.5 rounded-lg bg-blue-500 text-white font-semibold text-sm transition-all hover:bg-blue-400">
                  {t('login.continueToLogin')}
                </button>
              </div>
            </>
          )}
        </div>
        <p className="text-center text-slate-500 text-xs mt-6">
          {mode === 'login' ? (
            <>{t('login.noAccount')} <button type="button" onClick={switchMode} className="text-pink-400 hover:text-pink-300 underline">{t('login.register')}</button></>
          ) : (
            <>{t('login.haveAccount')} <button type="button" onClick={switchMode} className="text-pink-400 hover:text-pink-300 underline">{t('login.signIn')}</button></>
          )}
        </p>
      </form>
    </div>
  )
}
