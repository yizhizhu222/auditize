import { useState, useEffect } from 'react'
import { useT } from '../context/LanguageContext'

interface Asset {
  id: string
  title: string
  description: string
  language: string
  source_task_id: string | null
  created_at: string
}

interface TeamSummary {
  id: string
  name: string
}

interface AssetLibraryProps {
  onBack: () => void
}

export default function AssetLibrary({ onBack }: AssetLibraryProps) {
  const { t } = useT()
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [languageFilter, setLanguageFilter] = useState('')
  const [search, setSearch] = useState('')
  const [teams, setTeams] = useState<TeamSummary[]>([])
  const [teamFilter, setTeamFilter] = useState('')

  const token = localStorage.getItem('nexus-auth-token')
  const headers = { Authorization: `Bearer ${token}` }

  // Fetch user's teams on mount
  useEffect(() => {
    fetch('/api/v1/team/list', { headers })
      .then(r => r.json())
      .then(data => setTeams(data.teams || []))
      .catch((e) => { console.error('Failed to load teams:', e) })
  }, [])

  const fetchAssets = () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (languageFilter) params.set('language', languageFilter)
    if (search) params.set('search', search)
    if (teamFilter) params.set('team_id', teamFilter)

    fetch(`/api/v1/assets?${params.toString()}`, { headers })
      .then(r => r.json())
      .then(data => { setAssets(data.assets || []); setLoading(false) })
      .catch((e) => { console.error('Failed to load assets:', e); setLoading(false) })
  }

  useEffect(() => { fetchAssets() }, [languageFilter, teamFilter])

  const handleDelete = async (id: string) => {
    if (!confirm(t('assets.deleteConfirm'))) return
    await fetch(`/api/v1/assets/${id}`, { method: 'DELETE', headers })
    fetchAssets()
  }

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
        <h1 className="text-base font-semibold">{t('assets.codeAssets')}</h1>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 px-6 py-3 border-b"
        style={{ borderColor: 'var(--color-sub-border)' }}>
        <input
          type="text"
          placeholder={t('assets.searchPlaceholder')}
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') fetchAssets() }}
          className="flex-1 bg-transparent border rounded-lg px-3 py-1.5 text-xs focus:outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
        />
        <select
          value={languageFilter}
          onChange={e => setLanguageFilter(e.target.value)}
          className="bg-transparent border rounded-lg px-3 py-1.5 text-xs focus:outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
        >
          <option value="">{t('assets.allLanguages')}</option>
          <option value="python">{t('lang.python')}</option>
          <option value="javascript">{t('lang.javascript')}</option>
          <option value="go">{t('lang.go')}</option>
          <option value="cpp">{t('lang.cpp')}</option>
        </select>
        {teams.length > 0 && (
          <select
            value={teamFilter}
            onChange={e => setTeamFilter(e.target.value)}
            className="bg-transparent border rounded-lg px-3 py-1.5 text-xs focus:outline-none max-w-[140px]"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
          >
            <option value="">My Assets</option>
            {teams.map(team => (
              <option key={team.id} value={team.id}>{team.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Asset list */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-5 h-5 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
          </div>
        ) : assets.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
              style={{ backgroundColor: 'rgba(107,114,128,0.1)' }}>
              <svg className="w-6 h-6" style={{ color: 'var(--color-text-dim)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m6 4.125 2.25 2.25m0 0 2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
              </svg>
            </div>
            <p className="text-sm font-medium mb-1">{t('assets.noAssets')}</p>
            <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
              {t('assets.generateFirst')}
            </p>
          </div>
        ) : (
          <div className="grid gap-3 max-w-3xl">
            {assets.map(asset => (
              <div key={asset.id}
                className="rounded-xl border p-4 flex items-start justify-between gap-4"
                style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium truncate">{asset.title}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-pink-400/10 text-pink-400 uppercase">
                      {asset.language}
                    </span>
                  </div>
                  {asset.description && (
                    <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>
                      {asset.description}
                    </p>
                  )}
                  <p className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                    {t('assets.savedOn')} {new Date(asset.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(asset.id)}
                  className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors shrink-0"
                  title={t('assets.delete')}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
