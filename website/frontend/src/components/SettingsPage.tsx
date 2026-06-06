import { useState } from 'react'
import { useT } from '../context/LanguageContext'

interface SettingsPageProps { onBack?: () => void }

type TabId = 'api-keys' | 'profile'

export default function SettingsPage({ onBack }: SettingsPageProps) {
  const { t } = useT()
  const [tab, setTab] = useState<TabId>('api-keys')

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-3 px-6 h-14">
          {onBack && (
            <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-[#1C2128]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <h1 className="text-base font-semibold">{t('settings.title')}</h1>
        </div>
        <div className="flex gap-1 px-6 pb-3">
          {(['api-keys', 'profile'] as TabId[]).map(tabId => (
            <button key={tabId} onClick={() => setTab(tabId)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                tab === tabId ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'
              }`}>
              {t('settings.' + (tabId === 'api-keys' ? 'apiKeys' : 'profile'))}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
          Settings (API Keys, Profile, Theme) — full implementation available upon purchase
        </p>
      </div>
    </div>
  )
}
