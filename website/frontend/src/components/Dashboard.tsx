import { useState, useEffect, useRef } from 'react'
import { Download, Play, Terminal } from 'lucide-react'
import PigLogo from './PigLogo'
import SettingsPage from './SettingsPage'
import Sidebar from './Sidebar'
import AdminPage from './AdminPage'
import AssetLibrary from './AssetLibrary'
import ReviewPage from './ReviewPage'
import TeamPage from './TeamPage'
import MainPage from './MainPage'
import TaskHistory from './TaskHistory'
import SafetyReport from './SafetyReport'
import ErrorBoundary from './ErrorBoundary'
import { useSettings } from '../context/SettingsContext'
import { authHeaders } from '../lib/api'
import { useT } from '../context/LanguageContext'

interface ScanReport {
  verdict: string
  verdict_label: string
  verdict_description: string
  simple_summary: string
  what_it_does: string[]
  score: number
  total_issues: number
  finding_breakdown: Record<string, number>
  language: string
  scanned_lines: number
  categories: Record<string, any[]>
  findings: any[]
}

export default function Dashboard() {
  const { t } = useT()
  const { loadSettingsFromBackend, openAiKey, openRouterKey, deepSeekKey, anthropicKey, activeModel, activeProvider } = useSettings()
  const [activeNav, setActiveNav] = useState(() => {
    // If on admin port (8002), go straight to admin panel
    if (window.location.port === '8002') return 'admin'
    // Default to AI Tools page — new users land on scanner+templates, not empty team page
    return 'ai-tools'
  })
  const [userRole] = useState(() => localStorage.getItem('nexus-auth-role') || 'user')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  const [generating, setGenerating] = useState(false)
  const [latestTaskId, setLatestTaskId] = useState<string | null>(null)
  const [generatedCode, setGeneratedCode] = useState('')
  const [scanReport, setScanReport] = useState<ScanReport | null>(null)
  const [error, setError] = useState('')
  const [generatedLanguage, setGeneratedLanguage] = useState('python')

  const [previewTab, setPreviewTab] = useState<'code' | 'preview'>('code')
  const [previewOutput, setPreviewOutput] = useState<string | null>(null)
  const [previewRunning, setPreviewRunning] = useState(false)
  const [previewError, setPreviewError] = useState('')

  const codeRef = useRef<HTMLPreElement>(null)

  useEffect(() => { loadSettingsFromBackend() }, [loadSettingsFromBackend])

  // ── Notification polling ──
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/api/v1/notifications/unread-count', { headers: authHeaders() })
        if (res.ok) {
          const data = await res.json()
          setUnreadCount(data.count)
        }
      } catch { /* ignore */ }
    }
    poll()
    const interval = setInterval(poll, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleGenerate = async (idea: string, language: string) => {
    setGenerating(true)
    setError('')
    setScanReport(null)
    setGeneratedCode('')
    setLatestTaskId(null)
    setGeneratedLanguage(language)

    // ── Determine API key from active provider ──
    const providerKeyMap: Record<string, { storageKey: string; defaultModel: string }> = {
      'OpenAI':     { storageKey: 'nexus-settings-openai',     defaultModel: 'gpt-4o' },
      'OpenRouter': { storageKey: 'nexus-settings-openrouter', defaultModel: 'openai/gpt-4o' },
      'DeepSeek':   { storageKey: 'nexus-settings-deepseek',   defaultModel: 'deepseek-v4-flash' },
      'Anthropic':  { storageKey: 'nexus-settings-anthropic',  defaultModel: 'claude-sonnet-4-20250514' },
    }

    const provider = activeProvider || 'OpenAI'
    const providerCfg = providerKeyMap[provider] || providerKeyMap['OpenAI']
    let apiKey = ''
    if (provider === 'OpenAI') {
      apiKey = openAiKey || localStorage.getItem('nexus-settings-openai') || localStorage.getItem('nexus-settings-openAiKey') || ''
    } else {
      apiKey = localStorage.getItem(providerCfg.storageKey) || ''
      // Fallback to context state for inline key entry
      if (!apiKey) {
        if (provider === 'DeepSeek') apiKey = deepSeekKey
        else if (provider === 'OpenRouter') apiKey = openRouterKey
        else if (provider === 'Anthropic') apiKey = anthropicKey
      }
    }
    // Sentinel value means "use server key" — send empty string so backend auto-resolves
    if (apiKey === '__server_key__') apiKey = ''
    const model = activeModel || localStorage.getItem('nexus-settings-active_model') || providerCfg.defaultModel

    try {
      const res = await fetch('/api/v1/generate/stream', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ idea, language, api_key: apiKey, model, provider }),
      })

      if (!res.ok) {
        let detail = 'Generation failed'
        try {
          const d = await res.json()
          detail = d.detail || detail
        } catch {}
        setError(detail)
        setGenerating(false)
        return
      }

      // Stream the SSE response
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''
      let fullCode = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (!payload) continue

          try {
            const event = JSON.parse(payload)
            switch (event.type) {
              case 'token':
                fullCode += event.content
                setGeneratedCode(fullCode)
                break
              case 'code_done':
                fullCode = event.code
                setGeneratedCode(fullCode)
                break
              case 'scan':
                setScanReport(event.scan_result)
                break
              case 'done':
                setLatestTaskId(event.task_id)
                break
              case 'error':
                setError(event.detail || 'Generation failed')
                break
            }
          } catch {}
        }
      }
    } catch (err: any) {
      setError(err.message || 'Network error')
    } finally {
      setGenerating(false)
    }
  }

  const handleCopyCode = () => {
    if (generatedCode) navigator.clipboard.writeText(generatedCode)
  }

  const handleSaveToAssets = async () => {
    if (!latestTaskId || !generatedCode) return
    try {
      const res = await fetch('/api/v1/assets', {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ title: `Code from task ${latestTaskId.slice(0, 8)}`, language: generatedLanguage, code: generatedCode, source_task_id: latestTaskId }),
      })
      const data = await res.json()
      if (data.duplicate) alert('Already exists: ' + data.message)
      else alert('Saved to your asset library!')
    } catch { alert('Failed to save') }
  }

  const handleSubmitForReview = () => {
    if (latestTaskId) {
      sessionStorage.setItem('pending-review-task-id', latestTaskId)
      setActiveNav('reviews')
    }
  }

  const handleNavigate = (page: string) => {
    setActiveNav(page)
    setSidebarOpen(false)
  }

  const handleRunPreview = async () => {
    if (!generatedCode) return
    setPreviewRunning(true)
    setPreviewError('')
    setPreviewOutput(null)
    setPreviewTab('preview')
    try {
      const res = await fetch('/api/v1/compile', {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ code: generatedCode, language: generatedLanguage, stdin: '' }),
      })
      const data = await res.json()
      if (!res.ok) setPreviewError(data.detail || 'Run failed')
      else if (data.status === 'compile_error') setPreviewError(data.stderr || 'Compilation failed')
      else {
        setPreviewOutput(data.stdout || '(No output)')
        if (data.stderr) setPreviewOutput(prev => (prev || '') + '\n--- stderr ---\n' + data.stderr)
      }
    } catch { setPreviewError('Network error') }
    finally { setPreviewRunning(false) }
  }

  const handleExportZip = async () => {
    if (!latestTaskId) return
    try {
      const res = await fetch(`/api/v1/export/${latestTaskId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('nexus-auth-token')}` },
      })
      if (!res.ok) { alert('Export failed'); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `nexus-export-${latestTaskId.slice(0, 8)}.zip`; a.click()
      URL.revokeObjectURL(url)
    } catch { alert('Export failed') }
  }

  const handleBack = () => setActiveNav('')

  // ── Render helpers ──
  const renderAiTools = () => {
    // Still waiting for first token — show compact connecting indicator
    if (generating && !generatedCode) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="w-8 h-8 rounded-full border-2 border-pink-400 border-t-transparent animate-spin mx-auto mb-3" />
            <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>{t('results.generating2')}</p>
          </div>
        </div>
      )
    }
    // Tokens are streaming in — show code in real-time
    if (generating && generatedCode) {
      return (
        <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold">{t('results.title')}
              <span className="ml-2 text-[10px] font-normal inline-flex items-center gap-1" style={{ color: 'var(--color-text-dim)' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-pulse inline-block" />
                Generating...
              </span>
            </h2>
            <button onClick={() => { setGeneratedCode(''); setScanReport(null); setError(''); setLatestTaskId(null); setGenerating(false) }}
              className="px-3 py-1.5 rounded-lg text-xs border hover:bg-[#1C2128]" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
              {t('results.newIdea')}
            </button>
          </div>
          <div className="rounded-2xl border overflow-hidden" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
            <div className="px-5 py-3 border-b flex items-center gap-2" style={{ borderColor: 'var(--color-sub-border)' }}>
              <span className="text-xs font-medium">{t('results.code')}</span>
              <span className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>Streaming...</span>
            </div>
            <pre className="p-5 overflow-x-auto text-xs leading-relaxed font-mono max-h-[500px] overflow-y-auto"
              style={{ color: 'var(--color-text)', backgroundColor: 'var(--color-bg)' }}>
              {generatedCode || ''}
            </pre>
          </div>
        </div>
      )
    }
    if (error) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3" style={{ backgroundColor: 'rgba(239,68,68,0.1)' }}>
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="text-sm font-medium text-red-400 mb-2">{t('results.error')}</p>
            <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>{error}</p>
            <button onClick={() => { setError(''); setGeneratedCode(''); setScanReport(null) }}
              className="px-4 py-2 rounded-xl text-xs font-semibold hover:opacity-90" style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}>
              {t('results.tryAgain')}
            </button>
          </div>
        </div>
      )
    }
    if (generatedCode) {
      return (
        <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold">{t('results.title')}</h2>
            <button onClick={() => { setGeneratedCode(''); setScanReport(null); setError(''); setLatestTaskId(null) }}
              className="px-3 py-1.5 rounded-lg text-xs border hover:bg-[#1C2128]" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
              {t('results.newIdea')}
            </button>
          </div>
          {scanReport && <SafetyReport report={scanReport} />}

          <div className="rounded-2xl border overflow-hidden" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
            <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: 'var(--color-sub-border)' }}>
              <div className="flex items-center gap-1">
                <button onClick={() => setPreviewTab('code')}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${previewTab === 'code' ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'}`}>{t('results.code')}</button>
                <button onClick={() => { if (!previewOutput && !previewError) handleRunPreview() }}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1 ${previewTab === 'preview' ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'}`}>
                  <Terminal className="w-3 h-3" /> {t('results.preview')}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={handleRunPreview} disabled={previewRunning} className="p-1.5 rounded-lg hover:bg-[#1C2128] disabled:opacity-40" style={{ color: 'var(--color-text-muted)' }} title={t("results.run")}>
                  {previewRunning ? <div className="w-4 h-4 rounded-full border-2 border-gray-400 border-t-transparent animate-spin" /> : <Play className="w-4 h-4" />}
                </button>
                <button onClick={handleCopyCode} className="p-1.5 rounded-lg hover:bg-[#1C2128]" style={{ color: 'var(--color-text-muted)' }} title={t("results.copy")}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                  </svg>
                </button>
                <button onClick={handleSaveToAssets} className="p-1.5 rounded-lg hover:bg-[#1C2128]" style={{ color: 'var(--color-text-muted)' }} title={t("results.save")}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z" />
                  </svg>
                </button>
                <button onClick={handleExportZip} className="p-1.5 rounded-lg hover:bg-[#1C2128]" style={{ color: 'var(--color-text-muted)' }} title={t("results.downloadZip")}>
                  <Download className="w-4 h-4" />
                </button>
              </div>
            </div>
            {previewTab === 'code' && (
              <pre ref={codeRef} className="p-5 overflow-x-auto text-xs leading-relaxed font-mono max-h-[500px] overflow-y-auto"
                style={{ color: 'var(--color-text)', backgroundColor: 'var(--color-bg)' }}>
                {generatedCode || t('results.noCode')}
              </pre>
            )}
            {previewTab === 'preview' && (
              <div className="p-5 max-h-[500px] overflow-y-auto">
                {previewRunning && <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-muted)' }}><div className="w-3 h-3 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" /> Running...</div>}
                {previewError && <div className="rounded-lg p-3 text-xs font-mono" style={{ backgroundColor: 'rgba(239,68,68,0.08)', color: '#ef4444' }}>{previewError}</div>}
                {previewOutput && !previewRunning && <pre className="text-xs font-mono leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--color-text)' }}>{previewOutput}</pre>}
                {!previewError && !previewOutput && !previewRunning && <div className="text-xs" style={{ color: 'var(--color-text-dim)' }}>{t('results.clickRun')}</div>}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 pb-8">
            <button onClick={handleExportZip} className="px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2" style={{ backgroundColor: '#2EA043', color: '#fff' }}><Download className="w-4 h-4" /> {t('results.downloadZip')}</button>
            <button onClick={handleSubmitForReview} className="px-5 py-2.5 rounded-xl text-sm font-semibold border-2" style={{ borderColor: 'var(--color-accent)', color: 'var(--color-accent)' }}>{t('results.requestReview')}</button>
          </div>
        </div>
      )
    }
    return <MainPage onGenerate={handleGenerate} generating={generating} onNavigate={handleNavigate} />
  }

  return (
    <div className="h-screen overflow-hidden font-sans flex"
      style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)' }}>
      <div className="fixed top-0 left-0 right-0 z-20 flex items-center gap-3 px-4 h-12 border-b lg:hidden"
        style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)' }}>
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1 rounded" style={{ color: 'var(--color-text-muted)' }}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <PigLogo size={18} />
        <span className="text-sm font-semibold">Truffle AI</span>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 z-30 lg:hidden" onClick={() => setSidebarOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div className="relative w-[280px] h-full" onClick={(e) => e.stopPropagation()}>
            <Sidebar activeNav={activeNav} setActiveNav={handleNavigate} userRole={userRole} unreadCount={unreadCount} setUnreadCount={setUnreadCount} />
          </div>
        </div>
      )}

      <div className="hidden lg:block">
        <Sidebar activeNav={activeNav} setActiveNav={handleNavigate} userRole={userRole} unreadCount={unreadCount} setUnreadCount={setUnreadCount} />
      </div>

      <ErrorBoundary>
        {activeNav === '' ? (
          <div className="flex-1 flex min-w-0 overflow-hidden pt-12 lg:pt-0">
            <TeamPage />
          </div>
        ) : activeNav === 'ai-tools' ? (
          <div className="flex-1 flex min-w-0 overflow-hidden pt-12 lg:pt-0">
            {renderAiTools()}
          </div>
        ) : (
          <div className="flex-1 flex min-w-0 h-screen overflow-hidden pt-12 lg:pt-0">
            {activeNav === 'settings' && <SettingsPage onBack={handleBack} />}
            {activeNav === 'admin' && <AdminPage onBack={handleBack} />}
            {activeNav === 'assets' && <AssetLibrary onBack={handleBack} />}
            {activeNav === 'reviews' && <ReviewPage onBack={handleBack} />}
            {activeNav === 'history' && <TaskHistory onBack={handleBack} />}
          </div>
        )}
      </ErrorBoundary>
    </div>
  )
}
