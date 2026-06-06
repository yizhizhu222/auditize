import { useState } from 'react'
import { useT } from '../context/LanguageContext'

interface LoginProps {
  onLoginSuccess: () => void
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const { t } = useT()
  const [mode, setMode] = useState<'login' | 'register'>('login')

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#0D1117] via-[#111827] to-[#0D1117] p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-pink-400 to-indigo-400 bg-clip-text text-transparent">
            {t('login.title')}
          </h1>
          <p className="text-sm text-slate-500 mt-1">{t('login.subtitle')}</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8">
          <div className="flex gap-2 mb-6">
            <button onClick={() => setMode('login')}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${mode === 'login' ? 'bg-pink-500/10 text-pink-400' : 'text-slate-500'}`}>
              {t('login.signIn')}
            </button>
            <button onClick={() => setMode('register')}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${mode === 'register' ? 'bg-pink-500/10 text-pink-400' : 'text-slate-500'}`}>
              {t('login.register')}
            </button>
          </div>

          <div className="space-y-4">
            <input type="text" placeholder={t('login.username')}
              className="w-full bg-transparent border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-pink-500/50" />
            <input type="password" placeholder={t('login.password')}
              className="w-full bg-transparent border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-pink-500/50" />
            {mode === 'register' && (
              <input type="text" placeholder={t('login.email')}
                className="w-full bg-transparent border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-pink-500/50" />
            )}
            <button className="w-full py-2.5 rounded-xl bg-pink-500 hover:bg-pink-400 text-white font-medium text-sm transition-colors">
              {mode === 'login' ? t('login.signIn') : t('login.createAccount')}
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-600 text-center mt-6">
          Authentication (JWT + TOTP + email verification) — full implementation available upon purchase
        </p>
      </div>
    </div>
  )
}
