import { useState, useEffect, useRef } from 'react'
import PigLogo from './PigLogo'
import { useT } from '../context/LanguageContext'
import { authHeaders } from '../lib/api'
import type { Lang } from '../lib/translations'

interface SidebarProps {
  activeNav: string
  setActiveNav: (v: string) => void
  userRole?: string
  unreadCount?: number
  setUnreadCount?: (n: number) => void
}

interface Notification {
  id: number
  type: string
  title: string
  message: string
  related_id: string
  is_read: boolean
  created_at: string
}

const NavIcon = ({ type }: { type: string }) => {
  const props = { className: "w-5 h-5", fill: "none", stroke: "currentColor", viewBox: "0 0 24 24", strokeWidth: 1.5 }
  switch (type) {
    case 'home':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
        </svg>
      )
    case 'assets':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m6 4.125 2.25 2.25m0 0 2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z" />
        </svg>
      )
    case 'reviews':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" />
        </svg>
      )
    case 'settings':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        </svg>
      )
    case 'team':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        </svg>
      )
    case 'ai-tools':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
        </svg>
      )
    case 'admin':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
        </svg>
      )
    case 'history':
      return (
        <svg {...props}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
        </svg>
      )
    default:
      return null
  }
}

// ── Notification Bell Icon ──
function BellIcon({ count }: { count: number }) {
  return (
    <span className="relative inline-flex">
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
      </svg>
      {count > 0 && (
        <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-pink-500 text-[9px] font-bold text-white px-1 leading-none">
          {count > 99 ? '99+' : count}
        </span>
      )}
    </span>
  )
}

export default function Sidebar({ activeNav, setActiveNav, userRole, unreadCount = 0, setUnreadCount }: SidebarProps) {
  const { t, lang, setLang } = useT()
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loadingNotifs, setLoadingNotifs] = useState(false)
  const notifRef = useRef<HTMLDivElement>(null)

  // Determine which nav items to show based on role
  const role = userRole || 'user'
  const isMember = role === 'user'
  const isAdmin = role === 'admin'

  const navItems: Array<{ key: string; labelKey: string; icon: string }> = [
    { key: '', labelKey: 'sidebar.team', icon: 'home' },
  ]
  // All users get the core navigation
  navItems.push({ key: 'ai-tools', labelKey: 'sidebar.aiTools', icon: 'ai-tools' })
  navItems.push({ key: 'assets', labelKey: 'sidebar.assets', icon: 'assets' })
  navItems.push({ key: 'reviews', labelKey: 'sidebar.expertReview', icon: 'reviews' })
  navItems.push({ key: 'settings', labelKey: 'sidebar.settings', icon: 'settings' })
  navItems.push({ key: 'history', labelKey: 'sidebar.history', icon: 'history' })
  // Admin-only nav
  if (isAdmin) {
    navItems.push({ key: 'admin', labelKey: 'sidebar.adminPanel', icon: 'admin' })
  }

  const handleLogout = () => {
    localStorage.removeItem('nexus-auth-token')
    localStorage.removeItem('nexus-auth-role')
    window.location.reload()
  }

  const toggleLang = () => {
    setLang(lang === 'en' ? 'zh' : 'en')
  }

  const isActive = (nav: string) => nav === activeNav || (nav === '' && activeNav === '')
  const navStyle = (nav: string) =>
    `flex items-center gap-3 w-full px-3 py-2.5 rounded-lg transition-colors text-sm cursor-pointer ${
      isActive(nav)
        ? 'text-pink-400 bg-[#1C2128]'
        : 'text-[#8D96A0] hover:text-white hover:bg-[#1C2128]'
    }`

  // ── Notification dropdown handlers ──
  const toggleNotif = async () => {
    setNotifOpen(prev => !prev)
    if (!notifOpen) {
      setLoadingNotifs(true)
      try {
        const res = await fetch('/api/v1/notifications?unread_only=true&limit=20', { headers: authHeaders() })
        if (res.ok) {
          const data = await res.json()
          setNotifications(data.notifications || [])
        }
      } catch (e) { console.error('Failed to load notifications:', e) }
      setLoadingNotifs(false)
    }
  }

  const markRead = async (id: number) => {
    try {
      await fetch(`/api/v1/notifications/${id}/read`, { method: 'PUT', headers: authHeaders() })
      setNotifications(prev => prev.filter(n => n.id !== id))
      if (setUnreadCount) setUnreadCount(Math.max(0, unreadCount - 1))
    } catch (e) { console.error('Failed to mark notification read:', e) }
  }

  const markAllRead = async () => {
    try {
      await fetch('/api/v1/notifications/read-all', { method: 'PUT', headers: authHeaders() })
      setNotifications([])
      if (setUnreadCount) setUnreadCount(0)
    } catch (e) { console.error('Failed to mark all read:', e) }
  }

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false)
      }
    }
    if (notifOpen) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [notifOpen])

  return (
    <aside className="w-[240px] shrink-0 border-r flex flex-col h-full overflow-hidden"
      style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)' }}
    >
      {/* Logo */}
      <div className="h-14 flex items-center gap-3 px-5 shrink-0 border-b"
        style={{ borderColor: 'var(--color-sub-border)' }}>
        <div className="w-8 h-8 flex items-center justify-center">
          <PigLogo size={32} />
        </div>
        <span className="font-semibold text-base tracking-wide">Truffle AI</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-0.5 px-3 pt-4 overflow-y-auto">
        {navItems.map(item => (
          <button key={item.key} onClick={() => setActiveNav(item.key)} className={navStyle(item.key)}>
            <NavIcon type={item.icon} />
            <span>{t(item.labelKey as any)}</span>
          </button>
        ))}
      </nav>

      {/* Bottom: Notifications + Language + Logout */}
      <div className="p-3 border-t shrink-0 space-y-1" style={{ borderColor: 'var(--color-sub-border)' }}>
        {/* Notification bell */}
        <div ref={notifRef} className="relative">
          <button onClick={toggleNotif}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm transition-colors text-[#8D96A0] hover:text-white hover:bg-[#1C2128]">
            <BellIcon count={unreadCount} />
            <span className="flex-1 text-left">{t('sidebar.notifications')}</span>
          </button>

          {/* Notification dropdown */}
          {notifOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-1 rounded-xl border overflow-hidden shadow-xl z-50"
              style={{
                backgroundColor: 'var(--color-panel)',
                borderColor: 'var(--color-border)',
                maxHeight: '360px',
              }}>
              <div className="flex items-center justify-between px-4 py-2.5 border-b text-xs font-medium"
                style={{ borderColor: 'var(--color-sub-border)' }}>
                <span style={{ color: 'var(--color-text)' }}>{t('sidebar.notifications')}</span>
                {notifications.length > 0 && (
                  <button onClick={markAllRead} className="text-pink-400 hover:opacity-80">
                    {t('sidebar.markAllRead')}
                  </button>
                )}
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: '300px' }}>
                {loadingNotifs ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="w-5 h-5 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="text-xs text-center py-8 px-4" style={{ color: 'var(--color-text-dim)' }}>
                    {t('sidebar.noNotifications')}
                  </div>
                ) : (
                  notifications.map(n => (
                    <button key={n.id} onClick={() => markRead(n.id)}
                      className="w-full text-left px-4 py-3 border-b hover:bg-[#1C2128] transition-colors last:border-b-0"
                      style={{ borderColor: 'var(--color-sub-border)' }}>
                      <div className="flex items-start gap-2">
                        <span className="mt-0.5 shrink-0">
                          {n.type === 'approved' ? '✅' : n.type === 'rejected' ? '❌' : n.type === 'duplicate' ? '📎' : '🔔'}
                        </span>
                        <div className="min-w-0">
                          <p className="text-xs font-medium truncate" style={{ color: 'var(--color-text)' }}>{n.title}</p>
                          <p className="text-[10px] mt-0.5 line-clamp-2" style={{ color: 'var(--color-text-dim)' }}>{n.message}</p>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Language toggle */}
        <button onClick={toggleLang}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm transition-colors text-[#8D96A0] hover:text-white hover:bg-[#1C2128]">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.78.147 2.653.255" />
          </svg>
          <span className="flex-1 text-left">{t('sidebar.language')}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-pink-400/10 text-pink-400 font-medium">
            {lang === 'en' ? 'EN' : '中文'}
          </span>
        </button>

        <button onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm transition-colors text-[#8D96A0] hover:text-red-400 hover:bg-red-500/5">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
          </svg>
          <span>{t('sidebar.logout')}</span>
        </button>
      </div>
    </aside>
  )
}
