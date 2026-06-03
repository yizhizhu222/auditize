import { useState, useEffect } from 'react'
import { useTheme, type ThemePreset } from '../context/ThemeContext'
import { useToast } from '../context/ToastContext'
import { useT } from '../context/LanguageContext'
import { apiFetch } from '../lib/api'
import { useSettings } from '../context/SettingsContext'

interface SettingsPageProps {
  onBack: () => void
}

const PRESETS: { id: ThemePreset; label: string; desc: string }[] = [
  { id: 'terminal', label: 'Terminal', desc: 'Green phosphor' },
  { id: 'nexus-default', label: 'Truffle Dark', desc: 'Dark blue' },
  { id: 'dracula', label: 'Dracula', desc: 'Dark purple' },
  { id: 'github-light', label: 'GitHub Light', desc: 'Light' },
  { id: 'monokai', label: 'Monokai', desc: 'Classic' },
]

type TabId = 'api' | 'profile'

export default function SettingsPage({ onBack }: SettingsPageProps) {
  const { t } = useT()
  const { themePreset, setThemePreset } = useTheme()
  const { showToast } = useToast()
  const { reloadKeysFromStorage } = useSettings()
  const [activeTab, setActiveTab] = useState<TabId>('api')

  // API keys — read from all known localStorage key formats
  const readKey = (key: string) => localStorage.getItem(key) || ''
  const [openAiKey, setOpenAiKey] = useState(() => readKey('nexus-settings-openai') || readKey('nexus-settings-openAiKey') || '')
  const [openRouterKey, setOpenRouterKey] = useState(() => readKey('nexus-settings-openrouter') || readKey('nexus-settings-openRouterKey') || '')
  const [deepSeekKey, setDeepSeekKey] = useState(() => readKey('nexus-settings-deepseek') || readKey('nexus-settings-deepSeekKey') || '')
  const [anthropicKey, setAnthropicKey] = useState(() => readKey('nexus-settings-anthropic') || readKey('nexus-settings-anthropicKey') || '')
  const [saving, setSaving] = useState(false)

  // Profile
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [emailVerified, setEmailVerified] = useState(false)
  const [verifCode, setVerifCode] = useState('')
  const [verifSent, setVerifSent] = useState(false)
  const [verifCooldown, setVerifCooldown] = useState(0)

  useEffect(() => {
    fetch('/api/v1/settings/profile', {
      headers: { Authorization: `Bearer ${localStorage.getItem('nexus-auth-token')}` },
    })
      .then(r => r.json())
      .then(data => {
        if (data.display_name) setDisplayName(data.display_name)
      })
      .catch((e: any) => { console.error('Failed to load profile:', e) })
    fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${localStorage.getItem('nexus-auth-token')}` },
    })
      .then(r => r.json())
      .then(data => {
        if (data.email) setEmail(data.email)
        if (data.email_verified !== undefined) setEmailVerified(data.email_verified)
      })
      .catch((e: any) => { console.error('Failed to load user info:', e) })
  }, [])

  const handleSaveKeys = async () => {
    setSaving(true)
    // Write to all known localStorage key formats for compatibility
    const keysToSave: Record<string, string> = {
      'nexus-settings-openai': openAiKey,
      'nexus-settings-openAiKey': openAiKey,
      'nexus-settings-openrouter': openRouterKey,
      'nexus-settings-openRouterKey': openRouterKey,
      'nexus-settings-deepseek': deepSeekKey,
      'nexus-settings-deepSeekKey': deepSeekKey,
      'nexus-settings-anthropic': anthropicKey,
      'nexus-settings-anthropicKey': anthropicKey,
    }
    for (const [k, v] of Object.entries(keysToSave)) {
      localStorage.setItem(k, v)
    }

    // Sync keys to SettingsContext so provider/model selectors update immediately
    reloadKeysFromStorage()
    showToast('API keys saved locally', 'success')
    setSaving(false)
  }

  const handleSaveProfile = async () => {
    try {
      await fetch('/api/v1/settings/profile', {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('nexus-auth-token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ display_name: displayName }),
      })
      showToast('Profile updated', 'success')
    } catch {
      showToast('Failed to update profile', 'error')
    }
  }

  const tabs = [
    { id: 'api' as TabId, label: t('settings.apiKeys'), icon: '🔑' },
    { id: 'profile' as TabId, label: t('settings.profile'), icon: '👤' },
  ]

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 h-14 shrink-0 border-b"
        style={{ borderColor: 'var(--color-border)' }}>
        <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-[#1C2128] transition-colors"
          style={{ color: 'var(--color-text-muted)' }}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <h1 className="text-base font-semibold">{t('settings.title')}</h1>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Tab sidebar */}
        <div className="w-48 shrink-0 border-r p-4 space-y-1"
          style={{ borderColor: 'var(--color-border)' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 w-full px-3 py-2.5 rounded-lg text-sm transition-colors ${
                activeTab === tab.id
                  ? 'text-pink-400 bg-[#1C2128]'
                  : 'text-[#8D96A0] hover:text-white hover:bg-[#1C2128]'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}

          {/* Theme (always visible) */}
          <div className="pt-6">
            <p className="text-[10px] font-medium uppercase tracking-wider mb-2 px-3"
              style={{ color: 'var(--color-text-dim)' }}>
              {t('settings.theme')}
            </p>
            <div className="space-y-1">
              {PRESETS.map(p => (
                <button
                  key={p.id}
                  onClick={() => setThemePreset(p.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                    themePreset === p.id
                      ? 'text-pink-400 bg-[#1C2128]'
                      : 'text-[#8D96A0] hover:text-white hover:bg-[#1C2128]'
                  }`}
                >
                  <div className="font-medium">{p.label}</div>
                  <div className="text-[10px] text-[#484F58]">{p.desc}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'api' && (
            <div className="max-w-xl space-y-6">
              <div>
                <h2 className="text-lg font-semibold">{t('settings.apiKeys')}</h2>
                <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                  {t('settings.apiKeysDesc')}
                </p>
              </div>

              <InputField label="OpenAI" value={openAiKey} onChange={setOpenAiKey} placeholder="sk-..." />
              <InputField label="OpenRouter" value={openRouterKey} onChange={setOpenRouterKey} placeholder="sk-or-..." />
              <InputField label="DeepSeek" value={deepSeekKey} onChange={setDeepSeekKey} placeholder="sk-..." />
              <InputField label="Anthropic" value={anthropicKey} onChange={setAnthropicKey} placeholder="sk-ant-..." />

              <button
                onClick={handleSaveKeys}
                disabled={saving}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-40"
                style={{ backgroundColor: 'var(--color-accent)' }}
              >
                {saving ? t('settings.saving') : t('settings.saveKeys')}
              </button>
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="max-w-xl space-y-6">
              <div>
                <h2 className="text-lg font-semibold">{t('settings.profile')}</h2>
                <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                  Your display name shown in the app.
                </p>
              </div>

              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--color-text-dim)' }}>
                  {t('settings.displayName')}
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                />
              </div>

              {/* Email & verification */}
              {email && (
                <div>
                  <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--color-text-dim)' }}>
                    Email
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{email}</span>
                    {emailVerified ? (
                      <span className="text-green-400 text-xs">✅ Verified</span>
                    ) : (
                      <span className="text-yellow-400 text-xs">⚠️ Not verified</span>
                    )}
                  </div>
                  {!emailVerified && (
                    <div className="mt-3 space-y-2">
                      {!verifSent ? (
                        <button
                          onClick={async () => {
                            try {
                              await apiFetch('/api/v1/auth/send-verification-code', {
                                method: 'POST', headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ email }),
                              })
                              setVerifSent(true)
                              setVerifCooldown(60)
                              const timer = setInterval(() => {
                                setVerifCooldown(prev => {
                                  if (prev <= 1) { clearInterval(timer); return 0 }
                                  return prev - 1
                                })
                              }, 1000)
                            } catch (err: any) {
                              alert(err.message || 'Failed to send')
                            }
                          }}
                          className="text-xs text-pink-400 hover:text-pink-300 underline"
                        >
                          Send verification code
                        </button>
                      ) : (
                        <div className="flex items-center gap-2">
                          <input
                            type="text" maxLength={6} placeholder="6-digit code" value={verifCode}
                            onChange={e => setVerifCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            className="w-28 bg-transparent border rounded-lg px-3 py-1.5 text-sm focus:outline-none"
                            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                          />
                          <button
                            onClick={async () => {
                              try {
                                await apiFetch('/api/v1/auth/verify-email', {
                                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ email, code: verifCode }),
                                })
                                setEmailVerified(true)
                                alert('Email verified successfully!')
                              } catch (err: any) {
                                alert(err.message || 'Verification failed')
                              }
                            }}
                            disabled={verifCode.length !== 6}
                            className="text-xs px-3 py-1.5 rounded-lg bg-blue-500 text-white font-semibold disabled:opacity-40"
                          >
                            Verify
                          </button>
                          <button
                            onClick={async () => {
                              setVerifSent(false)
                              setVerifCode('')
                            }}
                            disabled={verifCooldown > 0}
                            className="text-xs text-slate-500 hover:text-slate-300 underline disabled:opacity-40"
                          >
                            {verifCooldown > 0 ? `${verifCooldown}s` : 'Resend'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={handleSaveProfile}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-90"
                style={{ backgroundColor: 'var(--color-accent)' }}
              >
                {t('settings.saveProfile')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Reusable input field ── */
function InputField({
  label, value, onChange, placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  const [show, setShow] = useState(false)
  return (
    <div>
      <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--color-text-dim)' }}>
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="flex-1 bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none font-mono"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
        />
        <button
          onClick={() => setShow(!show)}
          className="p-2 rounded-lg hover:bg-[#1C2128] transition-colors"
          style={{ color: 'var(--color-text-muted)' }}
          title={show ? 'Hide' : 'Show'}
        >
          {show ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}
