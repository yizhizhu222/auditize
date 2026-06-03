import { useState, useEffect } from 'react'
import { useT } from '../context/LanguageContext'
import SafetyReport from './SafetyReport'
import { authHeaders } from '../lib/api'

interface TaskSummary {
  id: string
  idea: string
  language: string
  status: string
  created_at: string
  updated_at: string
}

interface TaskDetail extends TaskSummary {
  code: string
  error_message: string
  scan_report: any
}

interface TaskHistoryProps {
  onBack: () => void
}

export default function TaskHistory({ onBack }: TaskHistoryProps) {
  const { t } = useT()
  const [tasks, setTasks] = useState<TaskSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detailMap, setDetailMap] = useState<Record<string, TaskDetail>>({})
  const [detailLoading, setDetailLoading] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/generate/tasks', { headers: authHeaders() })
      .then(r => r.json())
      .then(data => {
        setTasks(data.tasks || [])
        setTotal(data.total || 0)
      })
      .catch((e) => { console.error('Failed to load tasks:', e) })
      .finally(() => setLoading(false))
  }, [])

  const loadDetail = async (taskId: string) => {
    if (detailMap[taskId]) return // already loaded
    setDetailLoading(taskId)
    try {
      const res = await fetch(`/api/v1/generate/tasks/${taskId}`, { headers: authHeaders() })
      if (res.ok) {
        const data = await res.json()
        setDetailMap(prev => ({ ...prev, [taskId]: data }))
      }
    } catch (e) { console.error('Failed to load task detail:', e) }
    setDetailLoading(null)
  }

  const toggleExpand = (taskId: string) => {
    if (expandedId === taskId) {
      setExpandedId(null)
    } else {
      setExpandedId(taskId)
      loadDetail(taskId)
    }
  }

  const statusBadge = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-emerald-500/10 text-emerald-400'
      case 'generating': return 'bg-pink-500/10 text-pink-400'
      case 'failed': return 'bg-red-500/10 text-red-400'
      case 'pending': return 'bg-yellow-500/10 text-yellow-400'
      default: return 'bg-gray-500/10 text-gray-400'
    }
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
        <h1 className="text-base font-semibold">Task History</h1>
        <span className="ml-auto text-xs" style={{ color: 'var(--color-text-dim)' }}>
          {total} {total === 1 ? 'task' : 'tasks'}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-5 h-5 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-24">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
              style={{ backgroundColor: 'rgba(6,182,212,0.1)' }}>
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}
                style={{ color: 'var(--color-accent)' }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
              </svg>
            </div>
            <p className="text-sm font-medium mb-1">No generation tasks yet</p>
            <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
              Go to AI Tools and describe an idea to generate code
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map(task => (
              <div key={task.id}
                className="rounded-xl border overflow-hidden"
                style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
                {/* Summary row */}
                <div
                  className="flex items-start gap-4 px-5 py-4 cursor-pointer transition-colors hover:bg-[#1C2128]"
                  onClick={() => toggleExpand(task.id)}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{task.idea}</p>
                    <p className="text-[10px] font-mono mt-1" style={{ color: 'var(--color-text-dim)' }}>
                      {task.language} · {new Date(task.created_at).toLocaleDateString()} · {task.id.slice(0, 8)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${statusBadge(task.status)}`}>
                      {task.status}
                    </span>
                    <svg className={`w-4 h-4 transition-transform ${expandedId === task.id ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
                      style={{ color: 'var(--color-text-dim)' }}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                    </svg>
                  </div>
                </div>

                {/* Expanded detail */}
                {expandedId === task.id && (
                  <div className="border-t px-5 py-4 space-y-4" style={{ borderColor: 'var(--color-sub-border)' }}>
                    {detailLoading === task.id ? (
                      <div className="flex items-center justify-center h-20">
                        <div className="w-4 h-4 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
                      </div>
                    ) : detailMap[task.id] ? (
                      <>
                        {/* Scan report */}
                        {detailMap[task.id].scan_report && (
                          <SafetyReport report={detailMap[task.id].scan_report} />
                        )}

                        {/* Error message */}
                        {detailMap[task.id].error_message && (
                          <div className="rounded-lg p-3 text-xs text-red-400"
                            style={{ backgroundColor: 'rgba(239,68,68,0.08)' }}>
                            {detailMap[task.id].error_message}
                          </div>
                        )}

                        {/* Code */}
                        {detailMap[task.id].code && (
                          <div>
                            <p className="text-xs font-medium mb-2">Code</p>
                            <pre className="text-[10px] font-mono p-3 rounded-lg overflow-x-auto max-h-80 overflow-y-auto leading-relaxed"
                              style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text-dim)' }}>
                              {detailMap[task.id].code}
                            </pre>
                          </div>
                        )}
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
