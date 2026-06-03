import { useState, useEffect } from 'react'
import { useT } from '../context/LanguageContext'
import { authHeaders } from '../lib/api'

interface TeamInfo {
  in_team: boolean
  team_id?: string
  name?: string
  description?: string
  invite_code?: string
  members?: Array<{ user_id: number; username: string; role: string }>
  my_role?: string
}

interface FeatureRequest {
  id: string
  user_id: number
  username: string
  title: string
  description: string
  status: string
  linked_task_id: string | null
  duplicate_of: string | null
  reviewer_notes: string
  code: string
  created_at: string
  updated_at: string
}

interface TeamPageProps {
  onBack?: () => void
}

// ── Helpers ──

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-400',
  approved: 'bg-blue-400',
  generating: 'bg-pink-400',
  completed: 'bg-emerald-400',
  rejected: 'bg-red-400',
  duplicate: 'bg-gray-400',
}

const statusLabelKeys: Record<string, string> = {
  pending: 'team.pending',
  approved: 'team.approve',
  rejected: 'team.reject',
  duplicate: 'team.markDuplicate',
}

function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const colors = [
    'from-pink-400 to-pink-500',
    'from-cyan-400 to-blue-500',
    'from-purple-400 to-violet-500',
    'from-emerald-400 to-teal-500',
    'from-orange-400 to-rose-500',
  ]
  const idx = name.charCodeAt(0) % colors.length
  return (
    <div
      className={`rounded-xl bg-gradient-to-br ${colors[idx]} flex items-center justify-center text-white font-bold shrink-0`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      {name.charAt(0).toUpperCase()}
    </div>
  )
}

export default function TeamPage({ onBack }: TeamPageProps) {
  const { t } = useT()
  const [activeTab, setActiveTab] = useState<'board' | 'members'>('board')
  const [team, setTeam] = useState<TeamInfo | null>(null)
  const [requests, setRequests] = useState<FeatureRequest[]>([])
  const [loading, setLoading] = useState(true)

  // Create team form
  const [teams, setTeams] = useState<Array<{ team_id: string; name: string; my_role: string }>>([])
  const [selectedTeamId, setSelectedTeamId] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [teamName, setTeamName] = useState('')
  const [teamDesc, setTeamDesc] = useState('')
  const [creating, setCreating] = useState(false)

  // Join team form
  const [inviteCode, setInviteCode] = useState('')
  const [joining, setJoining] = useState(false)

  // Dialogs
  const [showInviteDialog, setShowInviteDialog] = useState(false)
  const [newInviteCode, setNewInviteCode] = useState('')
  const [showJoinDialog, setShowJoinDialog] = useState(false)
  const [joinResult, setJoinResult] = useState<{ team_id: string; name: string } | null>(null)

  // New request form
  const [showNewRequest, setShowNewRequest] = useState(false)
  const [reqTitle, setReqTitle] = useState('')
  const [reqDesc, setReqDesc] = useState('')
  const [submittingReq, setSubmittingReq] = useState(false)
  const [similarWarnings, setSimilarWarnings] = useState<Array<{ asset_id: string; title: string; similarity: number }>>([])

  // Review actions
  const [expandedReq, setExpandedReq] = useState<string | null>(null)
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')

  const showMsg = (msg: string) => { setMessage(msg); setTimeout(() => setMessage(''), 3000) }

  const handleLeaveTeam = async () => {
    if (!selectedTeamId) return
    if (!confirm(t('team.leaveConfirm'))) return
    try {
      const res = await fetch('/api/v1/team/leave?team_id=' + selectedTeamId, {
        method: 'POST', headers: authHeaders(),
      })
      if (res.ok) {
        showMsg(t('team.leftTeam'))
        loadTeamData()
      } else {
        const d = await res.json()
        showMsg(d.detail || t('team.failed'))
      }
    } catch { showMsg(t('team.networkError')) }
  }

  // ── Clean data loader ──
  const loadTeamData = async (teamId?: string) => {
    setLoading(true)
    try {
      const listRes = await fetch('/api/v1/team/list', { headers: authHeaders() })
      if (!listRes.ok) throw new Error('Failed to load teams')
      const listData = await listRes.json()
      const teamList = listData.teams || []

      setTeams(teamList)

      if (teamList.length === 0) {
        setTeam(null)
        setRequests([])
        setLoading(false)
        return
      }

      const tid = teamId || teamList[0].team_id
      setSelectedTeamId(tid)

      const [teamRes, reqRes] = await Promise.all([
        fetch('/api/v1/team/my?team_id=' + tid, { headers: authHeaders() }),
        fetch('/api/v1/team/requests?team_id=' + tid, { headers: authHeaders() }),
      ])

      if (teamRes.ok) {
        const teamData = await teamRes.json()
        setTeam(teamData)
        if (teamData.my_role !== 'owner') {
          setTeam({ ...teamData, invite_code: undefined })
        }
      } else {
        setTeam(null)
      }

      if (reqRes.ok) {
        const reqData = await reqRes.json()
        setRequests(reqData.requests || [])
      } else {
        setRequests([])
      }
    } catch (err) {
      console.error('loadTeamData error:', err)
      setTeam(null)
      setRequests([])
    }
    setLoading(false)
  }

  useEffect(() => { loadTeamData() }, [])

  const handleSwitchTeam = (newTeamId: string) => {
    setShowNewRequest(false)
    loadTeamData(newTeamId)
  }

  const handleDisbandTeam = async () => {
    if (!confirm(t('team.disbandConfirm'))) return
    try {
      const res = await fetch('/api/v1/team/disband?team_id=' + selectedTeamId, {
        method: 'POST', headers: authHeaders(),
      })
      if (res.ok) {
        showMsg(t('team.disbanded'))
        loadTeamData()
      } else {
        const d = await res.json()
        showMsg(d.detail || t('team.failed'))
      }
    } catch { showMsg(t('team.networkError')) }
  }

  const handleCreateTeam = async () => {
    if (!teamName.trim()) return
    setCreating(true)
    try {
      const res = await fetch('/api/v1/team/create', {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ name: teamName.trim(), description: teamDesc.trim() }),
      })
      const data = await res.json()
      if (res.ok) {
        setNewInviteCode(data.invite_code)
        setShowInviteDialog(true)
        setShowCreate(false)
        setTeamName('')
        setTeamDesc('')
        await loadTeamData(data.team_id)
      } else {
        showMsg(data.detail || t('team.failed'))
      }
    } catch { showMsg(t('team.networkError')) }
    setCreating(false)
  }

  const handleJoinTeam = async (code?: string) => {
    const codeToUse = code || inviteCode.trim()
    if (!codeToUse) return
    setJoining(true)
    try {
      const res = await fetch('/api/v1/team/join', {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ invite_code: codeToUse }),
      })
      const data = await res.json()
      if (res.ok) {
        setJoinResult({ team_id: data.team_id, name: data.name })
        setShowJoinDialog(true)
        setInviteCode('')
        setActiveTab('board')
        await loadTeamData(data.team_id)
      } else {
        showMsg(data.detail || t('team.invalidCode'))
      }
    } catch { showMsg(t('team.networkError')) }
    setJoining(false)
  }

  const handleSubmitRequest = async () => {
    if (!reqTitle.trim() || !selectedTeamId) return
    setSubmittingReq(true)
    try {
      const res = await fetch('/api/v1/team/requests?team_id=' + selectedTeamId, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ title: reqTitle.trim(), description: reqDesc.trim() }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.has_similar && data.similar_assets?.length > 0) {
          setSimilarWarnings(data.similar_assets)
        } else {
          setSimilarWarnings([])
        }
        showMsg(t('team.requestSubmitted'))
        setShowNewRequest(false)
        setReqTitle('')
        setReqDesc('')
        const reqRes = await fetch('/api/v1/team/requests?team_id=' + selectedTeamId, { headers: authHeaders() })
        if (reqRes.ok) setRequests((await reqRes.json()).requests || [])
      } else {
        const d = await res.json()
        showMsg(d.detail || t('team.failed'))
      }
    } catch { showMsg(t('team.networkError')) }
    setSubmittingReq(false)
  }

  const handleReview = async (requestId: string, decision: string) => {
    const notes = reviewNotes[requestId] || ''
    try {
      const body: any = { decision, notes }
      if (decision === 'duplicate') {
        const dupOf = prompt('Duplicate of which request ID?')
        if (!dupOf) return
        body.duplicate_of = dupOf
      }
      const res = await fetch(`/api/v1/team/requests/${requestId}/review`, {
        method: 'PUT', headers: authHeaders(),
        body: JSON.stringify(body),
      })
      if (res.ok) {
        showMsg(`Request ${decision}`)
        setExpandedReq(null)
        const reqRes = await fetch('/api/v1/team/requests?team_id=' + selectedTeamId, { headers: authHeaders() })
        if (reqRes.ok) setRequests((await reqRes.json()).requests || [])
      } else {
        const d = await res.json()
        showMsg(d.detail || t('team.failed'))
      }
    } catch { showMsg(t('team.networkError')) }
  }

  const handleGenerate = async (requestId: string, language = 'python') => {
    try {
      const res = await fetch(`/api/v1/team/requests/${requestId}/generate?language=${language}`, {
        method: 'POST', headers: authHeaders(),
      })
      const data = await res.json()
      if (res.ok) {
        showMsg(t('team.taskCreated'))
        const reqRes = await fetch('/api/v1/team/requests?team_id=' + selectedTeamId, { headers: authHeaders() })
        if (reqRes.ok) setRequests((await reqRes.json()).requests || [])
      } else {
        showMsg(data.detail || t('team.failed'))
      }
    } catch { showMsg(t('team.networkError')) }
  }

  const isReviewer = team?.my_role === 'reviewer' || team?.my_role === 'owner'

  // ── Dialogs ──
  const CreateDialog = showInviteDialog && newInviteCode ? (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="rounded-2xl border p-8 max-w-md w-full mx-auto text-center shadow-2xl"
        style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
          style={{ backgroundColor: 'rgba(244,114,182,0.15)' }}>
          <svg className="w-7 h-7 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
        </div>
        <h2 className="text-lg font-bold mb-2">{t('team.teamCreated')}</h2>
        <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
          {t('team.shareInvite')}
        </p>
        <div className="bg-[#1C2128] rounded-xl px-6 py-4 mb-6 inline-block">
          <code className="text-2xl font-bold tracking-widest" style={{ color: 'var(--color-accent)' }}>
            {newInviteCode}
          </code>
        </div>
        <div className="flex gap-3 justify-center">
          <button onClick={() => { navigator.clipboard.writeText(newInviteCode); showMsg(t('team.copied')) }}
            className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white"
            style={{ backgroundColor: 'var(--color-accent)' }}>
            {t('team.copyInvite')}
          </button>
          <button onClick={() => setShowInviteDialog(false)}
            className="px-6 py-2.5 rounded-xl text-sm font-medium"
            style={{ color: 'var(--color-text-muted)' }}>
            {t('team.close')}
          </button>
        </div>
      </div>
    </div>
  ) : null

  const JoinDialog = showJoinDialog && joinResult ? (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="rounded-2xl border p-8 max-w-md w-full mx-auto text-center shadow-2xl"
        style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
          style={{ backgroundColor: 'rgba(34,197,94,0.15)' }}>
          <svg className="w-7 h-7 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
        </div>
        <h2 className="text-lg font-bold mb-2">{t('team.joinedSuccess')}</h2>
        <p className="text-sm mb-2" style={{ color: 'var(--color-text-muted)' }}>
          {t('team.youAreMember')}
        </p>
        <p className="text-xl font-bold mb-6" style={{ color: 'var(--color-accent)' }}>
          {joinResult.name}
        </p>
        <button onClick={() => { setShowJoinDialog(false); setJoinResult(null) }}
          className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white"
          style={{ backgroundColor: 'var(--color-accent)' }}>
          {t('team.goToTeam')}
        </button>
      </div>
    </div>
  ) : null

  // ── No team: show create/join ──
  if (!loading && teams.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        {CreateDialog}
        {JoinDialog}
        <div className="max-w-md w-full space-y-6">
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5"
              style={{ backgroundColor: 'rgba(244,114,182,0.1)' }}>
              <svg className="w-8 h-8 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold mb-3">{t('team.yourTeamWorkspace')}</h1>
            <p className="text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>
              {t('team.notSetUp')}
            </p>
            <p className="text-xs mb-8" style={{ color: 'var(--color-text-dim)' }}>
              {t('team.setUpDesc')}
            </p>
          </div>

          {/* Create team card */}
          <div className="rounded-2xl border overflow-hidden transition-all hover:border-pink-500/30"
            style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
            <div className="px-6 py-5">
              <h2 className="text-sm font-semibold mb-3">{t('team.createTeam')}</h2>
              {showCreate ? (
                <div className="space-y-3">
                  <input type="text" value={teamName} onChange={e => setTeamName(e.target.value)}
                    placeholder={t('team.teamName')} maxLength={64}
                    className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-pink-500/50"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                  <input type="text" value={teamDesc} onChange={e => setTeamDesc(e.target.value)}
                    placeholder={t('team.teamDesc')} maxLength={200}
                    className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-pink-500/50"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                  <div className="flex gap-2 pt-1">
                    <button onClick={() => setShowCreate(false)}
                      className="px-4 py-2 rounded-xl text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                      {t('team.cancel')}
                    </button>
                    <button onClick={handleCreateTeam} disabled={creating || !teamName.trim()}
                      className="px-5 py-2 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all hover:opacity-90"
                      style={{ backgroundColor: 'var(--color-accent)' }}>
                      {creating ? t('team.creating') : t('team.create')}
                    </button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setShowCreate(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all hover:bg-[#1C2128]"
                  style={{ color: 'var(--color-accent)', border: '1px solid var(--color-accent)' }}>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  {t('team.newTeam')}
                </button>
              )}
            </div>
          </div>

          {/* Join team card */}
          <div className="rounded-2xl border overflow-hidden"
            style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
            <div className="px-6 py-5">
              <h2 className="text-sm font-semibold mb-3">{t('team.joinTeam')}</h2>
              <div className="flex gap-2">
                <input type="text" value={inviteCode} onChange={e => setInviteCode(e.target.value)}
                  placeholder={t('team.enterInviteCode')} maxLength={12}
                  className="flex-1 bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-pink-500/50 font-mono"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                <button onClick={() => handleJoinTeam()} disabled={joining || !inviteCode.trim()}
                  className="px-5 py-2 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all hover:opacity-90"
                  style={{ backgroundColor: 'var(--color-accent)' }}>
                  {joining ? t('team.joining') : t('team.join')}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-6 h-6 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
      </div>
    )
  }

  // ── Team view ──
  const isHome = !onBack

  const teamSwitcher = teams.length > 1 ? (
    <div className="flex items-center gap-1.5 px-1 py-1 rounded-xl"
      style={{ backgroundColor: 'var(--color-panel)' }}>
      {teams.map(t => (
        <button key={t.team_id} onClick={() => handleSwitchTeam(t.team_id)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
            selectedTeamId === t.team_id
              ? 'text-white shadow-sm'
              : 'text-[#8D96A0] hover:text-white'
          }`}
          style={{
            backgroundColor: selectedTeamId === t.team_id ? 'var(--color-accent)' : 'transparent',
          }}>
          {t.name}
        </button>
      ))}
    </div>
  ) : null

  const pendingCount = requests.filter(r => r.status === 'pending').length

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {CreateDialog}
      {JoinDialog}

      {/* ── Header ── */}
      <div className="shrink-0 border-b" style={{ borderColor: 'var(--color-border)' }}>
        {isHome ? (
          <div className="px-6 pt-6 pb-4">
            {/* Header row: team identity left, switcher right */}
            <div className="flex items-start gap-4">
              <div className="flex items-center gap-4 min-w-0 flex-1">
                <Avatar name={team?.name || 'T'} size={52} />
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <h1 className="text-xl font-bold truncate">{team?.name || t('team.noTeam')}</h1>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                      style={{
                        backgroundColor: team?.my_role === 'owner' ? 'rgba(168,85,247,0.1)' : team?.my_role === 'reviewer' ? 'rgba(59,130,246,0.1)' : 'rgba(107,114,128,0.1)',
                        color: team?.my_role === 'owner' ? '#a855f7' : team?.my_role === 'reviewer' ? '#3b82f6' : '#9ca3af',
                      }}>
                      {team?.my_role === 'owner' ? t('team.owner') : team?.my_role === 'reviewer' ? t('team.reviewer') : t('team.member')}
                    </span>
                    {/* Invite code inline (owner only) */}
                    {team?.my_role === 'owner' && team?.invite_code && (
                      <button onClick={() => { navigator.clipboard.writeText(team.invite_code!); showMsg(t('team.copied')) }}
                        className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-mono transition-all hover:bg-[#1C2128]"
                        style={{ backgroundColor: 'var(--color-panel)', color: 'var(--color-text-dim)' }}>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                        </svg>
                        <span className="text-pink-400 font-semibold">{team.invite_code}</span>
                      </button>
                    )}
                  </div>
                  {team?.description && (
                    <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>
                      {team.description}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                      {team?.members?.length || 0} {t('team.members')}
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                      {requests.length} {t('team.requests')}
                    </span>
                    {pendingCount > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 font-medium">
                        {pendingCount} {t('team.pending')}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Team switcher on the right */}
              {teamSwitcher && (
                <div className="shrink-0">
                  {teamSwitcher}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 px-6 h-14">
            <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-[#1C2128] transition-colors"
              style={{ color: 'var(--color-text-muted)' }}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {teamSwitcher || (
              <h1 className="text-base font-semibold">{team?.name || 'Team'}</h1>
            )}
          </div>
        )}

        {/* Tab bar */}
        <div className="flex gap-1 px-6 py-3">
          <button onClick={() => setActiveTab('board')}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === 'board'
                ? 'text-pink-400 bg-pink-400/10'
                : 'text-[#484F58] hover:text-[#8D96A0]'
            }`}>
            {t('team.requestBoard')} ({pendingCount})
          </button>
          <button onClick={() => setActiveTab('members')}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === 'members'
                ? 'text-pink-400 bg-pink-400/10'
                : 'text-[#484F58] hover:text-[#8D96A0]'
            }`}>
            {t('team.members')} ({team?.members?.length || 0})
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className="px-6 pt-3">
          <div className="rounded-xl border px-4 py-2.5 text-xs flex items-center gap-2"
            style={{ borderColor: 'rgba(34,211,238,0.3)', backgroundColor: 'rgba(34,211,238,0.06)', color: 'var(--color-accent)' }}>
            <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
            </svg>
            {message}
          </div>
        </div>
      )}

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'board' && (
          <div className="max-w-3xl mx-auto space-y-4">
            {/* New request button / form */}
            {!showNewRequest ? (
              <button onClick={() => setShowNewRequest(true)}
                className="flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium border-2 border-dashed w-full justify-center transition-all hover:bg-[#1C2128] hover:border-pink-500/30"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                {t('team.newRequest')}
              </button>
            ) : (
              <div className="rounded-2xl border p-5 space-y-3"
                style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                <input type="text" value={reqTitle} onChange={e => setReqTitle(e.target.value)}
                  placeholder={t('team.whatToBuild')} maxLength={128}
                  className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-pink-500/50"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                <textarea value={reqDesc} onChange={e => setReqDesc(e.target.value)}
                  placeholder={t('team.describeFeature')} rows={3}
                  className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-pink-500/50 resize-none"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                <div className="flex gap-2 pt-1">
                  <button onClick={() => { setShowNewRequest(false); setReqTitle(''); setReqDesc('') }}
                    className="px-4 py-2 rounded-xl text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    {t('team.cancel')}
                  </button>
                  <button onClick={handleSubmitRequest} disabled={submittingReq || !reqTitle.trim()}
                    className="px-5 py-2 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all hover:opacity-90"
                    style={{ backgroundColor: 'var(--color-accent)' }}>
                    {submittingReq ? t('team.submitting') : t('team.submitRequest')}
                  </button>
                </div>
              </div>
            )}

            {/* Similar warnings */}
            {similarWarnings.length > 0 && (
              <div className="rounded-xl border p-4 space-y-2"
                style={{ borderColor: 'rgba(249,115,22,0.3)', backgroundColor: 'rgba(249,115,22,0.06)' }}>
                <div className="flex items-center gap-2 text-xs font-semibold text-orange-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                  </svg>
                  {t('team.similarAssets')}
                </div>
                {similarWarnings.map(a => (
                  <div key={a.asset_id} className="flex items-center justify-between text-xs pl-6"
                    style={{ color: 'var(--color-text-muted)' }}>
                    <span className="truncate">{a.title}</span>
                    <span className="shrink-0 ml-2 font-mono text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                      {a.similarity}% match
                    </span>
                  </div>
                ))}
                <p className="text-[10px] pl-6 pt-1" style={{ color: 'var(--color-text-dim)' }}>
                  {t('team.checkAssets')}
                </p>
                <button onClick={() => setSimilarWarnings([])}
                  className="text-[10px] pl-6 underline" style={{ color: 'var(--color-accent)' }}>
                  {t('team.dismiss')}
                </button>
              </div>
            )}

            {/* Request cards */}
            {requests.length === 0 ? (
              <div className="text-center py-16">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-3"
                  style={{ backgroundColor: 'rgba(107,114,128,0.08)' }}>
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}
                    style={{ color: 'var(--color-text-dim)' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
                  </svg>
                </div>
                <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>
                  {t('team.noRequests')}
                </p>
              </div>
            ) : (
              requests.map(r => (
                <div key={r.id}
                  className="rounded-2xl border overflow-hidden transition-all hover:border-pink-500/20"
                  style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                  {/* Status color bar */}
                  <div className={`h-1 ${statusColors[r.status] || 'bg-gray-400'}`} />
                  <div className="p-5 cursor-pointer"
                    onClick={() => setExpandedReq(expandedReq === r.id ? null : r.id)}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold truncate">{r.title}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            r.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' :
                            r.status === 'approved' ? 'bg-blue-500/10 text-blue-400' :
                            r.status === 'generating' ? 'bg-pink-500/10 text-pink-400' :
                            r.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                            r.status === 'rejected' ? 'bg-red-500/10 text-red-400' :
                            'bg-gray-500/10 text-gray-400'
                          }`}>
                            {t(statusLabelKeys[r.status] || r.status) || r.status}
                          </span>
                        </div>
                        {r.description && (
                          <p className="text-xs mt-1 line-clamp-2" style={{ color: 'var(--color-text-muted)' }}>
                            {r.description.slice(0, 200)}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                          {r.username}
                        </span>
                        <svg className={`w-4 h-4 transition-transform ${expandedReq === r.id ? 'rotate-180' : ''}`}
                          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
                          style={{ color: 'var(--color-text-dim)' }}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  {/* Expanded: review actions */}
                  {expandedReq === r.id && isReviewer && r.status === 'pending' && (
                    <div className="border-t px-5 py-4 space-y-3"
                      style={{ borderColor: 'var(--color-sub-border)' }}>
                      <textarea value={reviewNotes[r.id] || ''}
                        onChange={e => setReviewNotes({ ...reviewNotes, [r.id]: e.target.value })}
                        placeholder={t('team.reviewerNotes')} rows={2}
                        className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-xs focus:outline-none focus:border-pink-500/50 resize-none"
                        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                      <div className="flex gap-2">
                        <button onClick={() => handleReview(r.id, 'approved')}
                          className="px-4 py-2 rounded-xl text-xs font-semibold text-white transition-all hover:opacity-90"
                          style={{ backgroundColor: '#2EA043' }}>
                          {t('team.approve')}
                        </button>
                        <button onClick={() => handleReview(r.id, 'rejected')}
                          className="px-4 py-2 rounded-xl text-xs font-medium transition-all hover:bg-red-500/5"
                          style={{ color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)' }}>
                          {t('team.reject')}
                        </button>
                        <button onClick={() => handleReview(r.id, 'duplicate')}
                          className="px-4 py-2 rounded-xl text-xs font-medium transition-all hover:bg-[#1C2128]"
                          style={{ color: 'var(--color-text-muted)', border: '1px solid var(--color-border)' }}>
                          {t('team.markDuplicate')}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Expanded: generate code */}
                  {expandedReq === r.id && r.status === 'approved' && isReviewer && (
                    <div className="border-t px-5 py-4 space-y-3"
                      style={{ borderColor: 'var(--color-sub-border)' }}>
                      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {t('team.approvedGenerate')}
                      </p>
                      <div className="flex items-center gap-2">
                        <select id={`gen-lang-${r.id}`} defaultValue="python"
                          className="text-xs px-3 py-2 rounded-lg border focus:outline-none cursor-pointer"
                          style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}>
                          <option value="python">{t('lang.python')}</option>
                          <option value="javascript">{t('lang.javascript')}</option>
                          <option value="go">{t('lang.go')}</option>
                          <option value="cpp">{t('lang.cpp')}</option>
                        </select>
                        <button onClick={() => {
                          const select = document.getElementById(`gen-lang-${r.id}`) as HTMLSelectElement
                          handleGenerate(r.id, select?.value || 'python')
                        }}
                          className="px-4 py-2 rounded-xl text-xs font-semibold text-white transition-all hover:opacity-90"
                          style={{ backgroundColor: 'var(--color-accent)' }}>
                          {t('team.generateCode')}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Expanded: reviewer notes */}
                  {expandedReq === r.id && r.reviewer_notes && (
                    <div className="border-t px-5 py-3"
                      style={{ borderColor: 'var(--color-sub-border)' }}>
                      <p className="text-[10px] font-medium mb-1" style={{ color: 'var(--color-text-dim)' }}>
                        {t('team.reviewerNotesLabel')}
                      </p>
                      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {r.reviewer_notes}
                      </p>
                    </div>
                  )}

                  {/* Expanded: duplicate info */}
                  {expandedReq === r.id && r.duplicate_of && (
                    <div className="border-t px-5 py-3"
                      style={{ borderColor: 'var(--color-sub-border)' }}>
                      <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
                        {t('team.markedDuplicate')} <span className="font-mono">{r.duplicate_of}</span>
                      </p>
                    </div>
                  )}

                  {/* Expanded: code preview */}
                  {expandedReq === r.id && r.code && (
                    <div className="border-t" style={{ borderColor: 'var(--color-sub-border)' }}>
                      <pre className="p-4 text-[10px] font-mono overflow-x-auto max-h-40"
                        style={{ color: 'var(--color-text-dim)', backgroundColor: 'var(--color-bg)' }}>
                        {r.code.slice(0, 1000)}
                      </pre>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'members' && (
          <div className="max-w-2xl mx-auto space-y-6">

            {/* Member list */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider px-1"
                style={{ color: 'var(--color-text-dim)' }}>
                {t('team.members')} ({team?.members?.length || 0})
              </h3>
              {team?.members?.map(m => (
                <div key={m.user_id}
                  className="rounded-xl border px-4 py-3 flex items-center justify-between transition-all hover:bg-[#1C2128]/50"
                  style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-pink-400 to-pink-500 flex items-center justify-center text-white text-sm font-bold">
                      {m.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{m.username}</p>
                      <p className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                        {m.role === 'owner' ? t('team.owner') : m.role === 'reviewer' ? t('team.reviewer') : t('team.member')}
                      </p>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2.5 py-1 rounded-full font-medium ${
                    m.role === 'owner' ? 'bg-purple-500/10 text-purple-400' :
                    m.role === 'reviewer' ? 'bg-blue-500/10 text-blue-400' :
                    'bg-gray-500/10 text-gray-400'
                  }`}>
                    {m.role === 'owner' ? t('team.owner') : m.role === 'reviewer' ? t('team.reviewer') : t('team.member')}
                  </span>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="space-y-2">
              {/* Join another team */}
              <div className="rounded-xl border p-4"
                style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-dim)' }}>
                  {t('team.joinAnotherTeam')}
                </p>
                <div className="flex gap-2">
                  <input type="text" value={inviteCode} onChange={e => setInviteCode(e.target.value)}
                    placeholder={t('team.enterInviteCode')} maxLength={12}
                    className="flex-1 bg-transparent border rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-pink-500/50 font-mono"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                  <button onClick={() => handleJoinTeam(inviteCode)}
                    disabled={joining || !inviteCode.trim()}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-white disabled:opacity-40 transition-all hover:opacity-90"
                    style={{ backgroundColor: 'var(--color-accent)' }}>
                    {joining ? t('team.joining') : t('team.join')}
                  </button>
                </div>
              </div>

              {/* Danger zone */}
              <div className="flex gap-2">
                {team?.my_role === 'owner' && (
                  <button onClick={handleDisbandTeam}
                    className="flex-1 px-4 py-2.5 rounded-xl text-xs font-medium border transition-all hover:bg-red-500/5"
                    style={{ borderColor: 'rgba(239,68,68,0.3)', color: '#ef4444' }}>
                    {t('team.disbandTeam')}
                  </button>
                )}
                {team && team.my_role && team.my_role !== 'owner' && (
                  <button onClick={handleLeaveTeam}
                    className="flex-1 px-4 py-2.5 rounded-xl text-xs font-medium border transition-all hover:bg-red-500/5"
                    style={{ borderColor: 'rgba(239,68,68,0.3)', color: '#ef4444' }}>
                    {t('team.leaveTeam')}
                  </button>
                )}
                <button onClick={() => setShowCreate(true)}
                  className="flex-1 px-4 py-2.5 rounded-xl text-xs font-medium border transition-all hover:bg-[#1C2128]"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-accent)' }}>
                  {t('team.createNewTeam')}
                </button>
              </div>

              {/* Inline create form */}
              {showCreate && (
                <div className="rounded-xl border p-4 space-y-2"
                  style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                  <input type="text" value={teamName} onChange={e => setTeamName(e.target.value)}
                    placeholder={t('team.teamName')} maxLength={64}
                    className="w-full bg-transparent border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-pink-500/50"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                  <input type="text" value={teamDesc} onChange={e => setTeamDesc(e.target.value)}
                    placeholder={t('team.teamDesc')} maxLength={200}
                    className="w-full bg-transparent border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-pink-500/50"
                    style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }} />
                  <div className="flex gap-2">
                    <button onClick={() => { setShowCreate(false); setTeamName(''); setTeamDesc('') }}
                      className="px-3 py-1.5 rounded-lg text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {t('team.cancel')}
                    </button>
                    <button onClick={handleCreateTeam} disabled={creating || !teamName.trim()}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white disabled:opacity-40 transition-all hover:opacity-90"
                      style={{ backgroundColor: 'var(--color-accent)' }}>
                      {creating ? t('team.creating') : t('team.create')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
