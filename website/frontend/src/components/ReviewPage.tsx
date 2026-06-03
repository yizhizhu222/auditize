import { useState, useEffect, useCallback } from 'react'
import { useT } from '../context/LanguageContext'
import SafetyReport from './SafetyReport'

interface Review {
  id: string
  task_id: string
  status: string
  admin_feedback: string
  admin_verdict: string
  idea: string
  language: string
  notes: string
  code: string
  scan_report: any
  created_at: string
  updated_at: string
}

interface ReviewPageProps {
  onBack: () => void
}

export default function ReviewPage({ onBack }: ReviewPageProps) {
  const { t } = useT()
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [taskId, setTaskId] = useState(() => {
    // Auto-fill from sessionStorage when coming from "Submit for Review"
    const pending = sessionStorage.getItem('pending-review-task-id')
    if (pending) {
      sessionStorage.removeItem('pending-review-task-id')
      return pending
    }
    return ''
  })
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const token = localStorage.getItem('nexus-auth-token')
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchReviews = useCallback(() => {
    setLoading(true)
    fetch('/api/v1/review/my-requests', { headers })
      .then(r => r.json())
      .then(data => { setReviews(data.reviews || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!taskId.trim()) return
    setSubmitting(true)
    setMessage('')

    try {
      const res = await fetch('/api/v1/review/submit', {
        method: 'POST',
        headers,
        body: JSON.stringify({ task_id: taskId.trim(), notes }),
      })
      const data = await res.json()
      if (res.ok) {
        setMessage(t('review.submittedMsg'))
        setTaskId('')
        setNotes('')
        fetchReviews()
      } else {
        setMessage(t('review.failed') + ': ' + (data.detail || ''))
      }
    } catch {
      setMessage(t('team.networkError'))
    } finally {
      setSubmitting(false)
    }
  }

  const statusColor = (s: string) => {
    switch (s) {
      case 'pending': return 'text-yellow-400 bg-yellow-500/10'
      case 'pending_payment': return 'text-purple-400 bg-purple-500/10'
      case 'completed': return 'text-emerald-400 bg-emerald-500/10'
      case 'changes_needed': return 'text-orange-400 bg-orange-500/10'
      case 'rejected': return 'text-red-400 bg-red-500/10'
      default: return 'text-gray-400 bg-gray-500/10'
    }
  }

  const handlePay = async (reviewId: string) => {
    try {
      const res = await fetch('/api/v1/payment/create-checkout-session', {
        method: 'POST',
        headers,
        body: JSON.stringify({ review_id: reviewId }),
      })
      const data = await res.json()
      if (res.ok && data.checkout_url) {
        window.location.href = data.checkout_url
      } else {
        setMessage(data.detail || 'Payment failed')
      }
    } catch {
      setMessage('Network error — payment unavailable')
    }
  }

  const [paymentCfg, setPaymentCfg] = useState<{ configured: boolean; price_dollars: string } | null>(null)
  useEffect(() => {
    fetch('/api/v1/payment/config', { headers })
      .then(r => r.json())
      .then(d => setPaymentCfg(d))
      .catch(() => {})
  }, [])

  const verdictBadge = (v: string) => {
    switch (v) {
      case 'approved': return 'bg-emerald-500/10 text-emerald-400'
      case 'changes_needed': return 'bg-orange-500/10 text-orange-400'
      case 'rejected': return 'bg-red-500/10 text-red-400'
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
        <h1 className="text-base font-semibold">{t('review.title')}</h1>
        <button onClick={fetchReviews}
          className="ml-auto p-1.5 rounded-lg hover:bg-[#1C2128] transition-colors"
          style={{ color: 'var(--color-text-muted)' }}
          title="Refresh">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full space-y-8">
        {/* Submit for review */}
        <div
          className="rounded-2xl border p-6"
          style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
        >
          <h2 className="text-sm font-semibold mb-1">{t('review.submitTitle')}</h2>
          <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>
            {t('review.submitDesc')}
          </p>
          {paymentCfg?.configured && (
            <div className="text-xs mb-4 px-3 py-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              💰 Expert review costs {paymentCfg.price_dollars}. You'll pay via Stripe after submitting.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--color-text-dim)' }}>
                {t('review.taskIdLabel')}
              </label>
              <input
                type="text"
                value={taskId}
                onChange={e => setTaskId(e.target.value)}
                placeholder={t('review.taskIdPlaceholder')}
                className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              />
            </div>
            <div>
              <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--color-text-dim)' }}>
                {t('review.notesLabel')}
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={3}
                placeholder={t('review.notesPlaceholder')}
                className="w-full bg-transparent border rounded-xl px-4 py-2.5 text-sm focus:outline-none resize-none"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              />
            </div>

            <button
              type="submit"
              disabled={!taskId.trim() || submitting}
              className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                !taskId.trim() || submitting ? 'opacity-40 cursor-not-allowed' : 'hover:opacity-90 cursor-pointer'
              }`}
              style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}
            >
              {submitting ? t('review.submitting') : t('review.submit')}
            </button>

            {message && (
              <p className="text-xs mt-2">{message}</p>
            )}
          </form>
        </div>

        {/* My review requests */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold">{t('review.myRequests')}</h2>
            <span className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
              {reviews.length} {reviews.length === 1 ? 'request' : 'requests'}
            </span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-20">
              <div className="w-4 h-4 rounded-full border-2 border-pink-400 border-t-transparent animate-spin" />
            </div>
          ) : reviews.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
                {t('review.noRequests')}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {reviews.map(review => (
                <div key={review.id}
                  className="rounded-xl border overflow-hidden"
                  style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
                >
                  {/* Summary row */}
                  <div
                    className="p-4 cursor-pointer hover:bg-[#1C2128] transition-colors"
                    onClick={() => setExpandedId(expandedId === review.id ? null : review.id)}
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{review.idea}</p>
                        <p className="text-[10px] font-mono mt-0.5" style={{ color: 'var(--color-text-dim)' }}>
                          {t('review.id')}: {review.id}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full ${statusColor(review.status)}`}>
                          {t('review.' + review.status) || review.status}
                        </span>
                        <svg className={`w-4 h-4 transition-transform ${expandedId === review.id ? 'rotate-180' : ''}`}
                          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
                          style={{ color: 'var(--color-text-dim)' }}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                        </svg>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
                      <span>{t('safety.language')}: {review.language}</span>
                      <span>·</span>
                      <span>{t('review.submittedOn')}: {new Date(review.created_at).toLocaleDateString()}</span>
                      {review.updated_at !== review.created_at && (
                        <>
                          <span>·</span>
                          <span>{t('review.repliedOn') || 'Replied'}: {new Date(review.updated_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {expandedId === review.id && (
                    <div className="border-t px-4 py-4 space-y-4" style={{ borderColor: 'var(--color-sub-border)' }}>
                      {/* Pending payment */}
                      {review.status === 'pending_payment' && paymentCfg?.configured && (
                        <button onClick={() => handlePay(review.id)}
                          className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-purple-500 hover:bg-purple-400 transition-all">
                          Pay {paymentCfg.price_dollars} & Unlock Review
                        </button>
                      )}

                      {/* Expert verdict & feedback */}
                      {(review.status === 'completed' || review.status === 'changes_needed' || review.status === 'rejected') && (
                        <>
                          {review.admin_verdict && (
                            <div className="rounded-xl border p-4" style={{ borderColor: 'var(--color-sub-border)' }}>
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-semibold">{t('review.verdict')}:</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${verdictBadge(review.admin_verdict)}`}>
                                  {review.admin_verdict?.replace(/_/g, ' ')}
                                </span>
                              </div>
                              {review.admin_feedback && (
                                <div className="text-xs leading-relaxed p-3 rounded-lg"
                                  style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text-muted)' }}>
                                  {review.admin_feedback}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Scan report */}
                          {review.scan_report && (
                            <div>
                              <p className="text-xs font-semibold mb-2">Code Analysis Report</p>
                              <SafetyReport report={review.scan_report} />
                            </div>
                          )}

                          {/* Generated code */}
                          {review.code && (
                            <div>
                              <p className="text-xs font-medium mb-2">Generated Code</p>
                              <pre className="text-[10px] font-mono p-3 rounded-lg overflow-x-auto max-h-80 overflow-y-auto leading-relaxed"
                                style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text-dim)' }}>
                                {review.code}
                              </pre>
                            </div>
                          )}
                        </>
                      )}

                      {/* Pending — no results yet */}
                      {review.status === 'pending' && (
                        <div className="text-center py-6">
                          <div className="w-6 h-6 rounded-full border-2 border-amber-400 border-t-transparent animate-spin mx-auto mb-2" />
                          <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
                            Waiting for expert review...
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
