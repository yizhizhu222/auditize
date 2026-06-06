import { useState } from 'react'
import PigLogo from './PigLogo'
import SettingsPage from './SettingsPage'
import Sidebar from './Sidebar'
import AssetLibrary from './AssetLibrary'
import ReviewPage from './ReviewPage'
import TeamPage from './TeamPage'
import MainPage from './MainPage'
import TaskHistory from './TaskHistory'
import ErrorBoundary from './ErrorBoundary'

interface ScanReport {
  verdict: string; verdict_label: string; verdict_description: string
  simple_summary: string; what_it_does: string[]
  score: number; total_issues: number
  finding_breakdown: Record<string, number>
  language: string; scanned_lines: number
  categories: Record<string, any[]>; findings: any[]
}

export default function Dashboard() {
  const [activeNav, setActiveNav] = useState(() => {
    if (window.location.port === '8002') return 'admin'
    return 'ai-tools'
  })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userRole] = useState(() => localStorage.getItem('nexus-auth-role') || 'user')

  const handleNavigate = (page: string) => {
    setActiveNav(page)
    setSidebarOpen(false)
  }
  const handleBack = () => setActiveNav('')
  const handleGenerate = (idea: string, language: string) => {}

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
            <Sidebar activeNav={activeNav} setActiveNav={handleNavigate} userRole={userRole} unreadCount={0} setUnreadCount={() => {}} />
          </div>
        </div>
      )}
      <div className="hidden lg:block">
        <Sidebar activeNav={activeNav} setActiveNav={handleNavigate} userRole={userRole} unreadCount={0} setUnreadCount={() => {}} />
      </div>

      <ErrorBoundary>
        {activeNav === '' ? (
          <div className="flex-1 flex min-w-0 overflow-hidden pt-12 lg:pt-0"><TeamPage /></div>
        ) : activeNav === 'ai-tools' ? (
          <div className="flex-1 flex min-w-0 overflow-hidden pt-12 lg:pt-0">
            <MainPage onGenerate={handleGenerate} generating={false} onNavigate={handleNavigate} />
          </div>
        ) : (
          <div className="flex-1 flex min-w-0 h-screen overflow-hidden pt-12 lg:pt-0">
            {activeNav === 'settings' && <SettingsPage onBack={handleBack} />}
            {activeNav === 'assets' && <AssetLibrary onBack={handleBack} />}
            {activeNav === 'reviews' && <ReviewPage onBack={handleBack} />}
            {activeNav === 'history' && <TaskHistory onBack={handleBack} />}
          </div>
        )}
      </ErrorBoundary>
    </div>
  )
}
