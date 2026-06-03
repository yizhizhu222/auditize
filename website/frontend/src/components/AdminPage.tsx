import { useState, useEffect } from 'react'
import { useT } from '../context/LanguageContext'

// ── Admin API: use relative path when on admin port, absolute when proxied ──
const ADMIN_API = window.location.port === '8002'
  ? '/api/v1/admin'
  : 'http://127.0.0.1:8002/api/v1/admin'

interface PendingReview {
  id: string; user_id: number; username: string; task_id: string
  notes: string; idea: string; language: string; code: string; submitted_at: string
}
interface ReviewRecord {
  id: string; user_id: number; username: string; task_id: string
  status: string; verdict: string; feedback: string; idea: string
  language: string; created_at: string; updated_at: string
}
interface AdminUser {
  id: number; username: string; email: string; display_name: string | null
  role: string; avatar_url: string | null; created_at: string; updated_at: string
}
interface TableInfo { name: string; columns: Array<{name: string; type: string}>; row_count: number }

interface AdminPageProps { onBack?: () => void }

const authHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('nexus-auth-token')
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

// ── Database Browser sub-component ──
function DataBrowser() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [columns, setColumns] = useState<string[]>([])
  const [rows, setRows] = useState<Record<string, any>[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage] = useState(50)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${ADMIN_API}/tables`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setTables(d.tables || []))
      .catch(() => setError('Cannot connect to admin server on port 8002'))
  }, [])

  const loadTable = async (name: string, p: number = 1) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${ADMIN_API}/table/${name}?page=${p}&per_page=${perPage}`, { headers: authHeaders() })
      if (!res.ok) { setError(`Failed to load table: ${res.statusText}`); return }
      const d = await res.json()
      setColumns(d.columns || [])
      setRows(d.rows || [])
      setTotal(d.total || 0)
      setPage(d.page || 1)
    } catch { setError('Failed to load table data') }
    finally { setLoading(false) }
  }

  const selectTable = (name: string) => {
    setSelected(name)
    setPage(1)
    loadTable(name, 1)
  }

  return (
    <div className="flex gap-4 h-full">
      {/* Table list sidebar */}
      <div className="w-56 shrink-0 overflow-y-auto border-r pr-3" style={{ borderColor: 'var(--color-sub-border)' }}>
        <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-dim)' }}>
          Tables ({tables.length})
        </p>
        {tables.length === 0 && !error && (
          <p className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>Loading...</p>
        )}
        {tables.map(t => (
          <button key={t.name} onClick={() => selectTable(t.name)}
            className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors mb-0.5 ${
              selected === t.name ? 'text-pink-400 bg-pink-400/10' : 'hover:bg-[#1C2128]'
            }`}
            style={{ color: selected === t.name ? undefined : 'var(--color-text)' }}>
            <span className="font-mono">{t.name}</span>
            <span className="ml-2 text-[10px]" style={{ color: 'var(--color-text-dim)' }}>({t.row_count})</span>
          </button>
        ))}
      </div>

      {/* Data view */}
      <div className="flex-1 overflow-hidden flex flex-col min-w-0">
        {error && <div className="text-xs text-red-400 mb-3">{error}</div>}

        {!selected && !error && (
          <div className="flex items-center justify-center h-32 text-xs" style={{ color: 'var(--color-text-dim)' }}>
            Select a table from the left to browse data
          </div>
        )}

        {selected && (
          <>
            {/* Table header info */}
            <div className="flex items-center justify-between mb-3 shrink-0">
              <div>
                <span className="text-sm font-semibold font-mono">{selected}</span>
                <span className="ml-2 text-xs" style={{ color: 'var(--color-text-dim)' }}>
                  {total} rows · page {page}/{Math.ceil(total / perPage) || 1}
                </span>
              </div>
              <div className="flex gap-1">
                <button onClick={() => loadTable(selected!, page - 1)} disabled={page <= 1 || loading}
                  className="px-3 py-1 rounded-lg text-[10px] border disabled:opacity-30 hover:bg-[#1C2128]"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
                  ← Prev
                </button>
                <button onClick={() => loadTable(selected!, page + 1)}
                  disabled={page * perPage >= total || loading}
                  className="px-3 py-1 rounded-lg text-[10px] border disabled:opacity-30 hover:bg-[#1C2128]"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
                  Next →
                </button>
              </div>
            </div>

            {/* Data table */}
            <div className="flex-1 overflow-auto rounded-xl border" style={{ borderColor: 'var(--color-border)' }}>
              {loading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="w-5 h-5 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
                </div>
              ) : rows.length === 0 ? (
                <div className="text-center py-16 text-xs" style={{ color: 'var(--color-text-dim)' }}>
                  Table is empty
                </div>
              ) : (
                <table className="w-full text-[11px]" style={{ color: 'var(--color-text)' }}>
                  <thead>
                    <tr className="sticky top-0" style={{ backgroundColor: 'var(--color-panel)' }}>
                      {columns.map(c => (
                        <th key={c} className="text-left px-3 py-2 font-semibold whitespace-nowrap border-b"
                          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-dim)' }}>
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--color-sub-border)' }}
                        className="hover:bg-[#1C2128] transition-colors">
                        {columns.map(c => (
                          <td key={c} className="px-3 py-1.5 whitespace-nowrap overflow-hidden text-ellipsis max-w-[250px]">
                            {row[c] === null ? <span style={{ color: 'var(--color-text-dim)' }}>NULL</span>
                              : typeof row[c] === 'object' ? JSON.stringify(row[c]).slice(0, 100)
                              : String(row[c])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main AdminPage ──
export default function AdminPage({ onBack }: AdminPageProps) {
  const { t } = useT()
  const [tab, setTab] = useState<'reviews' | 'history' | 'users' | 'database'>('reviews')
  const [pending, setPending] = useState<PendingReview[]>([])
  const [history, setHistory] = useState<ReviewRecord[]>([])
  const [users, setUsers] = useState<AdminUser[]>([])
  const [userTotal, setUserTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [feedbackMap, setFeedbackMap] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')
  const [adminOk, setAdminOk] = useState(true)

  const showMsg = (msg: string) => { setMessage(msg); setTimeout(() => setMessage(''), 3000) }

  const loadPending = async () => {
    try {
      const res = await fetch(`${ADMIN_API}/reviews/pending`, { headers: authHeaders() })
      if (res.ok) setPending((await res.json()).pending || [])
    } catch { setAdminOk(false) }
  }
  const loadHistory = async () => {
    try {
      const res = await fetch(`${ADMIN_API}/reviews/all`, { headers: authHeaders() })
      if (res.ok) setHistory((await res.json()).reviews || [])
    } catch (e) { console.error('Failed to load reviews:', e) }
  }
  const loadUsers = async () => {
    try {
      const res = await fetch(`${ADMIN_API}/users`, { headers: authHeaders() })
      if (res.ok) {
        const data = await res.json()
        setUsers(data.items || []); setUserTotal(data.total || 0)
      }
    } catch (e) { console.error('Failed to load users:', e) }
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([loadPending(), loadHistory(), loadUsers()]).finally(() => setLoading(false))
  }, [])

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      const res = await fetch(`${ADMIN_API}/users/${userId}/role`, {
        method: 'PUT', headers: authHeaders(), body: JSON.stringify({ role: newRole }),
      })
      if (res.ok) { showMsg(`User #${userId} role changed to ${newRole}`); loadUsers() }
      else { const d = await res.json(); showMsg(d.detail || 'Failed') }
    } catch { showMsg('Network error') }
  }

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!window.confirm(`Delete user "${username}" (#${userId})?`)) return
    try {
      const res = await fetch(`${ADMIN_API}/users/${userId}`, { method: 'DELETE', headers: authHeaders() })
      if (res.ok) { showMsg(`User #${userId} deleted`); loadUsers() }
      else { const d = await res.json(); showMsg(d.detail || 'Failed') }
    } catch { showMsg('Network error') }
  }

  const handleDecide = async (reviewId: string, verdict: string) => {
    const feedback = feedbackMap[reviewId] || ''
    if (verdict === 'rejected' && !feedback.trim()) { showMsg('Please provide feedback when rejecting'); return }
    try {
      const res = await fetch(`${ADMIN_API}/reviews/${reviewId}/decide`, {
        method: 'PUT', headers: authHeaders(), body: JSON.stringify({ verdict, feedback }),
      })
      if (res.ok) { showMsg(`Review ${verdict}`); loadPending(); loadHistory(); setExpandedId(null) }
      else { const d = await res.json(); showMsg(d.detail || 'Failed') }
    } catch { showMsg('Network error') }
  }

  const tabs = [
    { id: 'reviews' as const, label: `${t('admin.pendingReviews')} (${pending.length})` },
    { id: 'history' as const, label: t('admin.reviewHistory') },
    { id: 'users' as const, label: `Users (${userTotal})` },
    { id: 'database' as const, label: '📊 Database' },
  ]

  // ── Connection warning ──
  if (!adminOk) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: 'rgba(239,68,68,0.1)' }}>
            <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold mb-2">Admin server unreachable</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
            The admin server is not running on port 8002. Make sure both servers are started.
          </p>
          <p className="text-xs font-mono p-3 rounded-lg" style={{ backgroundColor: 'var(--color-panel)', color: 'var(--color-text-dim)' }}>
            ./start.sh now starts both services automatically.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Header */}
      <div className="flex items-center gap-3 px-6 h-14 shrink-0 border-b" style={{ borderColor: 'var(--color-border)' }}>
        {onBack && (
          <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-[#1C2128] transition-colors" style={{ color: 'var(--color-text-muted)' }}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>
        )}
        <h1 className="text-base font-semibold">{t('admin.title')}</h1>
        <span className="text-[9px] px-2 py-0.5 rounded-full font-mono ml-auto"
          style={{ backgroundColor: 'rgba(249,115,22,0.1)', color: '#f97316' }}>
          127.0.0.1:8002
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-6 py-3 border-b shrink-0" style={{ borderColor: 'var(--color-sub-border)' }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              tab === t.id ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Message toast */}
      {message && (
        <div className="px-6 pt-3">
          <div className="rounded-lg border px-4 py-2 text-sm" style={{ borderColor: 'rgba(34,211,238,0.3)', backgroundColor: 'rgba(34,211,238,0.06)', color: 'var(--color-accent)' }}>
            {message}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'reviews' && (
          loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-5 h-5 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
            </div>
          ) : pending.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3" style={{ backgroundColor: 'rgba(16,185,129,0.1)' }}>
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
              </div>
              <p className="text-sm font-medium mb-1">{t('admin.allCaughtUp')}</p>
              <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>{t('admin.noPending')}</p>
            </div>
          ) : (
            <div className="space-y-4 max-w-3xl">
              {pending.map(r => (
                <div key={r.id} className="rounded-2xl border overflow-hidden" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                  <div className="p-5 cursor-pointer" onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold truncate">{r.idea}</h3>
                        <p className="text-[10px] font-mono mt-0.5" style={{ color: 'var(--color-text-dim)' }}>
                          {t('admin.by')} {r.username} · {r.language} · {new Date(r.submitted_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 shrink-0">{t('admin.pending')}</span>
                    </div>
                    {r.notes && <p className="text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>{t('admin.note')}: {r.notes}</p>}
                  </div>
                  {expandedId === r.id && (
                    <div className="border-t px-5 py-4 space-y-4" style={{ borderColor: 'var(--color-sub-border)' }}>
                      <div>
                        <p className="text-xs font-medium mb-2">{t('admin.generatedCode')}</p>
                        <pre className="text-[10px] font-mono p-3 rounded-lg overflow-x-auto max-h-60 overflow-y-auto"
                          style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text-dim)' }}>
                          {r.code || t('admin.noCode')}
                        </pre>
                      </div>
                      <div>
                        <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--color-text-dim)' }}>{t('admin.yourFeedback')}</label>
                        <textarea value={feedbackMap[r.id] || ''} onChange={e => setFeedbackMap({...feedbackMap, [r.id]: e.target.value})}
                          rows={3} placeholder={t('admin.feedbackPlaceholder')}
                          className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-xs focus:outline-none resize-none"
                          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                      </div>
                      <div className="flex items-center gap-3">
                        <button onClick={() => handleDecide(r.id, 'approved')}
                          className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:opacity-90">✅ {t('admin.approve')}</button>
                        <button onClick={() => handleDecide(r.id, 'changes_needed')}
                          className="px-4 py-2 rounded-xl text-xs font-medium border border-orange-500/30 text-orange-400">🔧 {t('admin.requestChanges')}</button>
                        <button onClick={() => handleDecide(r.id, 'rejected')}
                          className="px-4 py-2 rounded-xl text-xs font-medium border border-red-500/30 text-red-400">❌ {t('admin.reject')}</button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        )}

        {tab === 'history' && (
          <div className="max-w-3xl">
            {history.length === 0 ? (
              <div className="text-center py-16"><p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>{t('admin.noHistory')}</p></div>
            ) : (
              <div className="space-y-2">
                {history.map(r => (
                  <div key={r.id} className="rounded-xl border p-4 flex items-start justify-between gap-4" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{r.idea}</p>
                      <p className="text-[10px] font-mono mt-0.5" style={{ color: 'var(--color-text-dim)' }}>{r.username} · {r.language}</p>
                      {r.feedback && <p className="text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>{r.feedback}</p>}
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full shrink-0 ${
                      r.verdict === 'approved' ? 'bg-emerald-500/10 text-emerald-400' :
                      r.verdict === 'changes_needed' ? 'bg-orange-500/10 text-orange-400' :
                      r.verdict === 'rejected' ? 'bg-red-500/10 text-red-400' : 'bg-gray-500/10 text-gray-400'}`}>
                      {r.verdict?.replace(/_/g, ' ') || r.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'users' && (
          <div className="max-w-4xl">
            {loading ? (
              <div className="flex items-center justify-center h-32"><div className="w-5 h-5 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" /></div>
            ) : users.length === 0 ? (
              <div className="text-center py-16"><p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>No users found</p></div>
            ) : (
              <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--color-text-dim)' }}>ID</th>
                      <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--color-text-dim)' }}>Username</th>
                      <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--color-text-dim)' }}>Email</th>
                      <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--color-text-dim)' }}>Role</th>
                      <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--color-text-dim)' }}>Created</th>
                      <th className="text-right px-4 py-3 font-medium" style={{ color: 'var(--color-text-dim)' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} style={{ borderBottom: '1px solid var(--color-sub-border)' }}>
                        <td className="px-4 py-3 font-mono text-[10px]" style={{ color: 'var(--color-text-dim)' }}>{u.id}</td>
                        <td className="px-4 py-3 font-medium">{u.username}</td>
                        <td className="px-4 py-3" style={{ color: 'var(--color-text-muted)' }}>{u.email || '—'}</td>
                        <td className="px-4 py-3">
                          <select value={u.role} onChange={e => handleRoleChange(u.id, e.target.value)}
                            className="text-[10px] px-2 py-1 rounded-lg bg-transparent border focus:outline-none cursor-pointer"
                            style={{ borderColor: 'var(--color-border)', color: u.role === 'admin' ? '#F472B6' : 'var(--color-text)' }}>
                            <option value="user">user</option>
                            <option value="admin">admin</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 font-mono text-[10px]" style={{ color: 'var(--color-text-dim)' }}>{new Date(u.created_at).toLocaleDateString()}</td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => handleDeleteUser(u.id, u.username)}
                            className="text-[10px] px-2.5 py-1 rounded-lg transition-colors hover:bg-red-500/10" style={{ color: '#ef4444' }}>Delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === 'database' && <DataBrowser />}
      </div>
    </div>
  )
}
