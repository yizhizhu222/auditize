import PigLogo from './PigLogo'

interface SidebarProps {
  activeNav: string
  setActiveNav: (nav: string) => void
  userRole: string
  unreadCount: number
  setUnreadCount: (n: number) => void
}

function NavIcon({ icon, active }: { icon: string; active: boolean }) {
  const color = active ? 'var(--color-accent)' : 'var(--color-text-dim)'
  const paths: Record<string, string> = {
    team: 'M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
    'ai-tools': 'M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z',
    assets: 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125',
    reviews: 'M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z',
    settings: 'M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z',
    history: 'M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
    admin: 'M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38a.485.485 0 0 1-.48-.03 8.996 8.996 0 0 1-3.744-4.311m0-9.18a9 9 0 0 1 3.744-4.311.485.485 0 0 1 .48-.03l.657.38c.524.302.71.962.463 1.511a16.863 16.863 0 0 0-.985 2.783m0 0a8.997 8.997 0 0 1 2.525-2.274m0 0a8.997 8.997 0 0 1 2.525 2.274m0 0c.688-.06 1.386-.09 2.09-.09h.75a4.5 4.5 0 1 1 0 9h-.75c-.704 0-1.402-.03-2.09-.09',
  }
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} style={{ color }}>
      <path strokeLinecap="round" strokeLinejoin="round" d={paths[icon] || paths.team} />
    </svg>
  )
}

const NAV_ITEMS = [
  { key: 'team', labelKey: 'sidebar.team', icon: 'team' },
  { key: 'ai-tools', labelKey: 'sidebar.aiTools', icon: 'ai-tools' },
  { key: 'assets', labelKey: 'sidebar.assets', icon: 'assets' },
  { key: 'reviews', labelKey: 'sidebar.expertReview', icon: 'reviews' },
  { key: 'settings', labelKey: 'sidebar.settings', icon: 'settings' },
  { key: 'history', labelKey: 'sidebar.history', icon: 'history' },
]

export default function Sidebar({ activeNav, setActiveNav, userRole, unreadCount }: SidebarProps) {
  return (
    <div className="h-full w-[240px] border-r flex flex-col"
      style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
      <div className="flex items-center gap-2.5 px-5 h-14 shrink-0 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <PigLogo size={20} />
        <span className="text-sm font-bold tracking-tight">Truffle AI</span>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
        {NAV_ITEMS.map(item => (
          <button key={item.key} onClick={() => setActiveNav(item.key)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeNav === item.key
                ? 'text-pink-400 bg-pink-400/10'
                : 'text-[#8D96A0] hover:text-white hover:bg-[#1C2128]'
            }`}>
            <NavIcon icon={item.icon} active={activeNav === item.key} />
            <span>{item.labelKey}</span>
          </button>
        ))}
        {userRole === 'admin' && (
          <button onClick={() => setActiveNav('admin')}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeNav === 'admin' ? 'text-pink-400 bg-pink-400/10' : 'text-[#8D96A0] hover:text-white hover:bg-[#1C2128]'
            }`}>
            <NavIcon icon="admin" active={activeNav === 'admin'} />
            <span>Admin Panel</span>
          </button>
        )}
      </nav>
      <div className="p-3 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <button onClick={() => { localStorage.removeItem('nexus-auth-token'); window.location.reload() }}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-[#8D96A0] hover:text-white hover:bg-[#1C2128] transition-all">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
          </svg>
          Logout
        </button>
      </div>
    </div>
  )
}
