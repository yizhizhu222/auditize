import { useState, useEffect, useRef } from 'react'
import {
  Sparkles,
  ShieldCheck,
  Users,
  Package,
  Contact,
  BarChart3,
  Receipt,
  Wrench,
  CalendarCheck,
  ArrowRight,
  Settings,
  ChevronDown,
  ChevronRight,
  Search,
} from 'lucide-react'
import SafetyReport from './SafetyReport'
import { authHeaders } from '../lib/api'
import { useT } from '../context/LanguageContext'
import { useSettings } from '../context/SettingsContext'

interface MainPageProps {
  onGenerate: (idea: string, language: string) => void
  generating: boolean
  onNavigate: (page: string) => void
}

const TEMPLATES: Array<{ icon: any; titleKey: string; descKey: string; prompt: string }> = [
  { icon: Package,   titleKey: 'template.inventory',  descKey: 'template.inventoryDesc',  prompt: 'Build an inventory management system with product tracking, stock inbound/outbound, low-stock alerts, purchase order management, and sales statistics dashboard. Include a simple web UI.' },
  { icon: Contact,   titleKey: 'template.crm',        descKey: 'template.crmDesc',        prompt: 'Build a customer relationship management system with contact management, follow-up tracking, contract management, sales funnel dashboard, and customer tagging. Include a simple web UI.' },
  { icon: BarChart3, titleKey: 'template.dashboard',   descKey: 'template.dashboardDesc',  prompt: 'Build a data visualization dashboard with line chart, bar chart, pie chart, date range filter, auto-refresh, and fullscreen mode. Include a simple web UI.' },
  { icon: Receipt,   titleKey: 'template.expense',     descKey: 'template.expenseDesc',    prompt: 'Build an expense reimbursement system where employees submit expenses, managers approve or reject, finance processes payments, with budget limits and expense history. Include a simple web UI.' },
  { icon: Wrench,    titleKey: 'template.ticket',      descKey: 'template.ticketDesc',     prompt: 'Build a ticket management system with ticket creation, auto-assignment, priority levels, progress tracking, completion confirmation, and ticket statistics. Include a simple web UI.' },
  { icon: CalendarCheck, titleKey: 'template.booking', descKey: 'template.bookingDesc',    prompt: 'Build a meeting room booking system with multiple room management, time slot booking, availability calendar, conflict detection, and my bookings view. Include a simple web UI.' },
]

const ONBOARDING_KEY = 'nexus-tour-done'
const SAMPLE_IDEA = 'Build a simple to-do list app with add, delete, and mark-complete. Use a clean web UI.'

function GuidedTour({ onFillSample, generating }: { onFillSample: () => void; generating: boolean }) {
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(ONBOARDING_KEY) === 'done')
  const [show, setShow] = useState(false)
  const tourRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!dismissed) {
      const timer = setTimeout(() => setShow(true), 500)
      return () => clearTimeout(timer)
    }
  }, [dismissed])

  useEffect(() => {
    if (show && tourRef.current) {
      tourRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [show])

  const dismiss = () => {
    setDismissed(true)
    setShow(false)
    localStorage.setItem(ONBOARDING_KEY, 'done')
  }

  if (dismissed || !show) return null

  return (
    <div ref={tourRef} className="rounded-2xl border mb-6 overflow-hidden transition-all animate-in fade-in slide-in-from-top-2 duration-500"
      style={{
        borderColor: 'var(--color-border)',
        backgroundColor: 'var(--color-panel)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
      }}>
      <div className="px-5 py-4">
        <div className="flex items-start gap-4 mb-3">
          <span className="text-2xl shrink-0 mt-0.5">🚀</span>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
              Welcome to TruffleKit!
            </h3>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
              Tell AI what you want to build in plain English — it writes the code, scans for security, and your team can review it. No coding needed.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => { onFillSample(); setTimeout(() => { const ta = document.querySelector('textarea'); ta?.focus(); ta?.scrollIntoView({ behavior: 'smooth', block: 'center' }) }, 200) }}
            disabled={generating}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-white transition-all hover:opacity-90 disabled:opacity-40"
            style={{ backgroundColor: 'var(--color-accent)' }}>
            ✨ Try a sample — I'll fill in an idea for you
          </button>
          <button onClick={dismiss}
            className="px-3 py-2 rounded-xl text-xs font-medium transition-all hover:bg-[#1C2128]"
            style={{ color: 'var(--color-text-muted)' }}>
            I know what I'm doing ✕
          </button>
        </div>
      </div>
    </div>
  )
}


const LANG_KEYS: Record<string, string> = { python: 'lang.python', javascript: 'lang.javascript', go: 'lang.go', cpp: 'lang.cpp' }
const SCAN_LANGUAGES = ['python', 'javascript', 'go', 'cpp']

export default function MainPage({ onGenerate, generating, onNavigate }: MainPageProps) {
  const { t } = useT()
  const [idea, setIdea] = useState('')
  const [language, setLanguage] = useState('python')
  const { activeProvider, setActiveProvider, activeModel, setActiveModel, configuredProviders, modelsByProvider, modelsLoading, reloadKeysFromStorage } = useSettings()
  const [modelSearch, setModelSearch] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [hasServerKey, setHasServerKey] = useState(false)
  // Inline API key entry state
  const [inlineKeys, setInlineKeys] = useState<Record<string, string>>(() => ({
    'OpenAI': localStorage.getItem('nexus-settings-openai') || '',
    'OpenRouter': localStorage.getItem('nexus-settings-openrouter') || '',
    'DeepSeek': localStorage.getItem('nexus-settings-deepseek') || '',
    'Anthropic': localStorage.getItem('nexus-settings-anthropic') || '',
  }))
  // ── Team state with selector ──
  const [userTeamList, setUserTeamList] = useState<Array<{ team_id: string; name: string }>>([])
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [teamInfo, setTeamInfo] = useState<{ in_team: boolean; name?: string; pending_count?: number } | null>(null)
  const [recentRequests, setRecentRequests] = useState<any[]>([])

  // Check if the server has a shared API key configured
  useEffect(() => {
    fetch('/api/v1/config')
      .then(r => r.json())
      .then(data => {
        const hasKey = data.has_server_key ?? false
        setHasServerKey(hasKey)
        if (hasKey) {
          // Check if user has ANY personal key configured
          const hasUserKey = !!(
            localStorage.getItem('nexus-settings-deepseek') ||
            localStorage.getItem('nexus-settings-openai') ||
            localStorage.getItem('nexus-settings-openrouter') ||
            localStorage.getItem('nexus-settings-anthropic')
          )
          // Mark DeepSeek as server-configured (shows 🔑) if user hasn't set their own key
          if (!hasUserKey) {
            setInlineKeys(prev => ({ ...prev, 'DeepSeek': '__server_key__' }))
            setActiveProvider('DeepSeek')
            setActiveModel('deepseek-chat')
          }
        }
      })
      .catch(() => setHasServerKey(false))
  }, [])

  const loadTeamData = async (teamId?: string) => {
    try {
      const listRes = await fetch('/api/v1/team/list', { headers: authHeaders() })
      const listData = await listRes.json()
      const teamList = listData.teams || []
      setUserTeamList(teamList)
      if (teamList.length === 0) {
        setTeamInfo(null)
        setRecentRequests([])
        return
      }
      const tid = teamId || teamList[0].team_id
      setSelectedTeamId(tid)
      const [teamRes, reqRes] = await Promise.all([
        fetch(`/api/v1/team/my?team_id=${tid}`, { headers: authHeaders() }),
        fetch(`/api/v1/team/requests?team_id=${tid}`, { headers: authHeaders() }),
      ])
      if (teamRes.ok) {
        const teamData = await teamRes.json()
        setTeamInfo(teamData)
      }
      if (reqRes.ok) {
        const reqData = await reqRes.json()
        setRecentRequests(reqData.requests?.slice(0, 5) || [])
      }
    } catch (e) { console.error('Failed to load team data:', e) }
  }

  const handleSwitchTeam = (tid: string) => {
    loadTeamData(tid)
  }

  useEffect(() => {
    loadTeamData()
  }, [])
  const [scanCode, setScanCode] = useState('')
  const [scanLang, setScanLang] = useState('python')
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState<any>(null)
  const [scanError, setScanError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim() || generating) return
    onGenerate(idea.trim(), language)
  }

  const handleTemplate = (prompt: string) => {
    setIdea(prompt)
    // Scroll to the input so user can see what was filled
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    // Focus the textarea
    setTimeout(() => {
      const ta = document.querySelector('textarea')
      if (ta) ta.focus()
    }, 300)
  }

  const handleInlineKey = (provider: string, key: string) => {
    setInlineKeys(prev => ({ ...prev, [provider]: key }))
    const storageKeyMap: Record<string, string> = {
      'OpenAI': 'nexus-settings-openai',
      'OpenRouter': 'nexus-settings-openrouter',
      'DeepSeek': 'nexus-settings-deepseek',
      'Anthropic': 'nexus-settings-anthropic',
    }
    const sk = storageKeyMap[provider]
    if (sk) {
      localStorage.setItem(sk, key)
      // Also sync to SettingsContext
      reloadKeysFromStorage()
    }
  }

  const handleScan = async () => {
    if (!scanCode.trim() || scanning) return
    setScanning(true)
    setScanResult(null)
    setScanError('')
    try {
      const res = await fetch('/api/v1/scan', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ code: scanCode, language: scanLang }),
      })
      if (!res.ok) {
        const d = await res.json()
        setScanError(d.detail || 'Scan failed')
        return
      }
      const data = await res.json()
      setScanResult(data.report)
    } catch {
      setScanError('Network error')
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8 lg:py-12">

        {/* ── Getting Started ── */}
        <GuidedTour onFillSample={() => setIdea(SAMPLE_IDEA)} generating={generating} />

        {/* ── Hero ── */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-medium mb-4"
            style={{ backgroundColor: 'rgba(6,182,212,0.1)', color: 'var(--color-accent)' }}>
            <Sparkles className="w-3 h-3" />
            {t('main.aiGenerator')}
          </div>
          <h1 className="text-3xl lg:text-4xl font-bold mb-4 leading-tight whitespace-pre-line"
            style={{ color: 'var(--color-text)' }}>
            {t('main.heroTitle')}
          </h1>
          <p className="text-sm max-w-2xl mx-auto leading-relaxed"
            style={{ color: 'var(--color-text-muted)' }}>
            {t('main.heroDesc')}
          </p>
        </div>

        {/* ── Value Props ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
          {[
            { icon: Sparkles, title: t('main.value1Title'), desc: t('main.value1Desc') },
            { icon: ShieldCheck, title: t('main.value2Title'), desc: t('main.value2Desc') },
            { icon: Users, title: t('main.value3Title'), desc: t('main.value3Desc') },
          ].map(v => (
            <div key={v.title}
              className="rounded-xl border p-4 text-center"
              style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-2"
                style={{ backgroundColor: 'rgba(6,182,212,0.1)', color: 'var(--color-accent)' }}>
                <v.icon className="w-4 h-4" />
              </div>
              <div className="text-sm font-semibold mb-1">{v.title}</div>
              <div className="text-[11px] leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
                {v.desc}
              </div>
            </div>
          ))}
        </div>

        {/* ════════════════════════════════════════════════════════════════ */}
        {/* ★ PASTE & SCAN — independent, no API key needed              */}
        {/* ════════════════════════════════════════════════════════════════ */}
        <div className="rounded-2xl border-2 border-dashed mb-6"
          style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-panel)' }}>
          <div className="px-5 pt-4 pb-3">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-md flex items-center justify-center"
                style={{ backgroundColor: 'rgba(6,182,212,0.1)', color: 'var(--color-accent)' }}>
                <ShieldCheck className="w-3.5 h-3.5" />
              </div>
              <span className="text-sm font-semibold">{t('main.pasteScan')}</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium ml-auto"
                style={{ backgroundColor: 'rgba(249,115,22,0.1)', color: '#f97316' }}>
                {t('main.noKeyNeeded')}
              </span>
            </div>
            <textarea
              value={scanCode}
              onChange={(e) => setScanCode(e.target.value)}
              placeholder={t('main.pastePlaceholder')}
              rows={4}
              className="w-full bg-transparent border rounded-xl px-4 py-3 text-xs font-mono focus:outline-none resize-none"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
            />
            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>{t('main.language')}</span>
                <div className="flex gap-1">
                  {SCAN_LANGUAGES.map(langId => (
                    <button key={langId} type="button" onClick={() => setScanLang(langId)}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
                        scanLang === langId
                          ? 'text-pink-400 bg-pink-400/10'
                          : 'text-[#484F58] hover:text-[#8D96A0]'
                      }`}>
                      {t(LANG_KEYS[langId])}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={handleScan} disabled={!scanCode.trim() || scanning}
                className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  !scanCode.trim() || scanning ? 'opacity-40 cursor-not-allowed' : 'hover:opacity-90 cursor-pointer'
                }`}
                style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}>
                {scanning ? (
                  <><div className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" /> {t('main.scanning')}</>
                ) : (
                  <><Search className="w-3 h-3" /> {t('main.scanForSafety')}</>
                )}
              </button>
            </div>
          </div>

          {/* Scan results inline */}
          {scanError && (
            <div className="px-5 pb-4">
              <div className="rounded-xl p-3 text-xs text-red-400"
                style={{ backgroundColor: 'rgba(239,68,68,0.08)' }}>
                {scanError}
              </div>
            </div>
          )}
          {scanResult && (
            <div className="px-5 pb-5">
              <SafetyReport report={scanResult} />
            </div>
          )}
        </div>

        {/* ── Templates ── */}
        <div className="mb-6">
          <h2 className="text-sm font-semibold mb-3">{t('main.quickStart')}</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {TEMPLATES.map(tmpl => (
              <button key={tmpl.titleKey} onClick={() => handleTemplate(tmpl.prompt)}
                disabled={generating}
                className="rounded-xl border p-3 text-left transition-all hover:scale-[1.02] hover:border-pink-500/30 disabled:opacity-40"
                style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                <div className="w-6 h-6 rounded-md flex items-center justify-center mb-2"
                  style={{ backgroundColor: 'rgba(6,182,212,0.08)', color: 'var(--color-accent)' }}>
                  <tmpl.icon className="w-3.5 h-3.5" />
                </div>
                <div className="text-xs font-semibold mb-0.5">{t(tmpl.titleKey)}</div>
                <div className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>{t(tmpl.descKey)}</div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Generate Input + Button ── */}
        <form onSubmit={handleSubmit}
          className="rounded-2xl border p-1 transition-all duration-200 focus-within:border-pink-500/50 focus-within:shadow-none mb-4"
          style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder={t('main.orDescribe')}
            rows={3}
            className="w-full bg-transparent resize-none px-4 py-3 text-sm focus:outline-none rounded-2xl"
            style={{ color: 'var(--color-text)' }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e)
            }}
          />
          <div className="flex items-center justify-between gap-4 px-1 pb-1 pt-2">
            <button type="button" onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-[11px] flex items-center gap-1 px-3 py-1.5 rounded-lg"
              style={{ color: 'var(--color-text-dim)' }}>
              {showAdvanced ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {t('main.advanced')}
            </button>

            {showAdvanced && (
              <div className="flex flex-wrap items-start gap-4 px-1 py-3">
                {/* Provider selector — always show all 4 providers */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-dim)' }}>Provider</span>
                  <div className="flex gap-1 flex-wrap">
                    {['OpenAI', 'OpenRouter', 'DeepSeek', 'Anthropic'].map(pid => {
                      const hasKey = !!inlineKeys[pid]
                      const isActive = activeProvider === pid
                      return (
                        <div key={pid} className="flex items-center gap-1">
                          <button type="button" onClick={() => { setActiveProvider(pid); setModelSearch('') }}
                            className={`px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                              isActive ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'
                            }`}>
                            {pid}{hasKey ? ' 🔑' : ''}
                          </button>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* API key input for active provider if no key stored */}
                {activeProvider && !inlineKeys[activeProvider] && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-dim)' }}>API Key</span>
                    <input type="password" value={inlineKeys[activeProvider] || ''}
                      onChange={e => handleInlineKey(activeProvider, e.target.value)}
                      placeholder={`Enter ${activeProvider} API key...`}
                      className="w-48 bg-transparent border rounded-lg px-2.5 py-1.5 text-[10px] font-mono focus:outline-none focus:border-pink-500/50"
                      style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                  </div>
                )}

                {/* Model selector with search (only if key exists for active provider) */}
                {activeProvider && inlineKeys[activeProvider] && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-dim)' }}>Model</span>
                    <div className="relative">
                      <input type="text" value={modelSearch} onChange={e => setModelSearch(e.target.value)}
                        placeholder="Search models..."
                        className="w-44 bg-transparent border rounded-lg px-2.5 py-1.5 text-[10px] font-mono focus:outline-none focus:border-pink-500/50"
                        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                      {modelSearch && (
                        <div className="absolute top-full left-0 right-0 mt-1 z-10 max-h-32 overflow-y-auto rounded-lg border"
                          style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                          {(modelsByProvider[activeProvider] || [])
                            .filter(m => m.id.toLowerCase().includes(modelSearch.toLowerCase()) || m.name.toLowerCase().includes(modelSearch.toLowerCase()))
                            .slice(0, 20)
                            .map(m => (
                              <button key={m.id} type="button"
                                onClick={() => { setActiveModel(m.id); setModelSearch('') }}
                                className={`w-full text-left px-2.5 py-1.5 text-[10px] font-mono transition-colors hover:bg-[#1C2128] ${
                                  activeModel === m.id ? 'text-pink-400 bg-pink-400/5' : 'text-[#8D96A0]'
                                }`}>
                                {m.name || m.id}
                              </button>
                            ))}
                          {(modelsByProvider[activeProvider] || []).length === 0 && !modelsLoading && (
                            <div className="px-2.5 py-1.5 text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                              No models loaded. Enter key above to fetch models.
                            </div>
                          )}
                          {modelsLoading && (
                            <div className="px-2.5 py-1.5 text-[10px] flex items-center gap-1.5" style={{ color: 'var(--color-text-dim)' }}>
                              <span className="w-2 h-2 rounded-full border border-pink-400 border-t-transparent animate-spin" />
                              Loading...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    {activeModel && !modelSearch && (
                      <span className="text-[10px] font-mono truncate max-w-44" style={{ color: 'var(--color-text-dim)' }}>
                        {activeModel}
                      </span>
                    )}
                  </div>
                )}

                {/* Language selector */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-dim)' }}>{t('main.language')}</span>
                  <div className="flex gap-1">
                    {SCAN_LANGUAGES.map(langId => (
                      <button key={langId} type="button" onClick={() => setLanguage(langId)}
                        className={`px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                          language === langId
                            ? 'text-pink-400 bg-pink-400/10'
                            : 'text-[#484F58] hover:text-[#8D96A0]'
                        }`}>
                        {t(LANG_KEYS[langId])}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <button type="submit" disabled={!idea.trim() || generating}
              className={`px-6 py-2.5 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 ${
                !idea.trim() || generating ? 'opacity-40 cursor-not-allowed' : 'hover:opacity-90 cursor-pointer'
              }`}
              style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}>
              {generating ? (
                <><div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" /> {t('main.generating')}</>
              ) : (
                <><Sparkles className="w-4 h-4" /> {t('main.generate')}</>
              )}
            </button>
          </div>
        </form>

        {/* ── Team Activity ── */}
        {(userTeamList.length > 0 || teamInfo?.in_team) && (
          <div className="border-t pt-6" style={{ borderColor: 'var(--color-sub-border)' }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"
                style={{ color: 'var(--color-text-dim)' }}>
                <Users className="w-3 h-3" />
                {teamInfo?.name || t('sidebar.team')} · {userTeamList.length}
                {recentRequests.length > 0 && ` · ${recentRequests.filter(r => r.status === 'pending').length} ${t('team.pending')}`}
              </h3>
              <button onClick={() => onNavigate('team')}
                className="text-[10px] flex items-center gap-1 px-2 py-1 rounded-lg"
                style={{ color: 'var(--color-accent)' }}>
                {t('teamActivity.viewAll')} <ArrowRight className="w-2.5 h-2.5" />
              </button>
            </div>
            {userTeamList.length > 1 && (
              <div className="mb-3">
                <select value={selectedTeamId} onChange={e => handleSwitchTeam(e.target.value)}
                  className="text-xs px-3 py-1.5 rounded-lg border focus:outline-none cursor-pointer"
                  style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}>
                  {userTeamList.map(t => (
                    <option key={t.team_id} value={t.team_id}>{t.name}</option>
                  ))}
                </select>
              </div>
            )}
            {recentRequests.length > 0 ? (
              <div className="space-y-1.5">
                {recentRequests.slice(0, 4).map((r: any) => (
                  <div key={r.id}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs"
                    style={{ backgroundColor: 'var(--color-panel)' }}>
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      r.status === 'pending' ? 'bg-yellow-400' :
                      r.status === 'completed' ? 'bg-emerald-400' :
                      r.status === 'approved' ? 'bg-blue-400' :
                      r.status === 'rejected' ? 'bg-red-400' : 'bg-gray-400'
                  }`} />
                  <span className="font-medium truncate">{r.title}</span>
                  <span className="text-[10px] shrink-0" style={{ color: 'var(--color-text-dim)' }}>{r.username}</span>
                  <span className="ml-auto text-[10px] shrink-0" style={{ color: 'var(--color-text-dim)' }}>
                    {r.status}
                  </span>
                </div>
              ))}
            </div>
            ) : (
              <div className="text-xs text-center py-3" style={{ color: 'var(--color-text-dim)' }}>
                {t('teamActivity.noActivity')}
              </div>
            )}
          </div>
        )}

        {/* ── No API key notice ── */}
        {configuredProviders.length === 0 && (
          <div className="mt-6 p-3 rounded-xl text-xs flex items-center justify-center gap-1.5 flex-wrap"
            style={{ backgroundColor: 'rgba(249,115,22,0.08)', color: '#f97316' }}>
            <Sparkles className="w-3 h-3" />
            {hasServerKey
              ? 'Using server API key. '
              : 'No API key configured — generation may fail. '}
            <button onClick={() => onNavigate('settings')} className="underline font-medium ml-0.5">
              Add your own key →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
