import { useT } from '../context/LanguageContext'

interface ScanFinding {
  risk: string; title: string; description: string; line: number; code_snippet: string; recommendation: string
}

interface ScanReport {
  verdict: string; verdict_label: string; verdict_description: string
  simple_summary: string; what_it_does: string[]
  score: number; total_issues: number
  finding_breakdown: Record<string, number>
  language: string; scanned_lines: number
  categories: Record<string, any[]>; findings: any[]
}

interface SafetyReportProps {
  report: ScanReport
}

function getScoreLabel(score: number): string {
  if (score === 0) return 'safe'
  if (score <= 20) return 'minor'
  if (score <= 50) return 'needsReview'
  return 'dangerous'
}

function ScoreGauge({ score, maxScore = 100, label, color }: { score: number; maxScore?: number; label: string; color: string }) {
  const r = 36, circumference = 2 * Math.PI * r, offset = circumference - (score / maxScore) * circumference
  return (
    <svg width="90" height="90" viewBox="0 0 90 90">
      <circle cx="45" cy="45" r={r} fill="none" stroke="#30363D" strokeWidth="6" />
      <circle cx="45" cy="45" r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={circumference} strokeDashoffset={offset}
        transform="rotate(-90 45 45)" strokeLinecap="round" />
      <text x="45" y="42" textAnchor="middle" fill="#E6EDF3" fontSize="16" fontWeight="bold">{score}</text>
      <text x="45" y="56" textAnchor="middle" fill="#8D96A0" fontSize="7">{label}</text>
    </svg>
  )
}

export default function SafetyReport({ report }: SafetyReportProps) {
  const { t } = useT()
  const scoreLabel = getScoreLabel(report.score)
  const verdictColors: Record<string, string> = {
    safe: '#2EA043', minor: '#f97316', needsReview: '#eab308', dangerous: '#ef4444'
  }
  const color = verdictColors[scoreLabel] || '#8D96A0'

  return (
    <div className="rounded-2xl border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-panel)' }}>
      <div className="p-5">
        <div className="flex items-center gap-6 mb-4">
          <ScoreGauge score={report.score} label={t('safety.safetyScore')} color={color} />
          <div>
            <div className="text-lg font-bold" style={{ color }}>{report.verdict_label || t('safety.' + scoreLabel)}</div>
            <div className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>{report.verdict_description}</div>
          </div>
        </div>
        <div className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
          Security scan report — detailed findings available in full version
        </div>
      </div>
    </div>
  )
}
