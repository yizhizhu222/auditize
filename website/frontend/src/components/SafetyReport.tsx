import {
  TriangleAlert,
  AlertTriangle,
  AlertCircle,
  Info,
  Lightbulb,
  ShieldCheck,
  Code,
  Gauge,
} from 'lucide-react'
import { useT } from '../context/LanguageContext'

interface ScanFinding {
  category: string
  risk_level: string
  risk_label: string
  risk_emoji: string
  title: string
  description: string
  line_number: number | null
  snippet: string | null
  recommendation: string
  finding_type?: string
}

interface ScanReport {
  verdict: string
  verdict_label: string
  verdict_description: string
  simple_summary: string
  what_it_does: string[]
  score: number
  quality_score?: number
  overall_score?: number
  total_issues: number
  security_issues?: number
  quality_issues?: number
  finding_breakdown: Record<string, number>
  quality_finding_breakdown?: Record<string, number>
  language: string
  scanned_lines: number
  categories: Record<string, Array<ScanFinding>>
  quality_findings?: ScanFinding[]
  findings: ScanFinding[]
}

interface SafetyReportProps {
  report: ScanReport
}

function getScoreLabel(score: number): { color: string; gaugeColor: string; labelKey: string } {
  if (score >= 60) return { color: 'red', gaugeColor: '#ef4444', labelKey: 'safety.dangerous' }
  if (score >= 30) return { color: 'orange', gaugeColor: '#f97316', labelKey: 'safety.needsReview' }
  if (score > 0) return { color: 'yellow', gaugeColor: '#eab308', labelKey: 'safety.minor' }
  return { color: 'emerald', gaugeColor: '#10b981', labelKey: 'safety.safe' }
}

function ScoreGauge({ score, label, safetyLabel, color }: { score: number; label: string; safetyLabel: string; color?: string }) {
  const { gaugeColor } = getScoreLabel(score)
  const strokeColor = color || gaugeColor
  return (
    <div className="flex items-center gap-4">
      <div className="relative w-14 h-14">
        <svg className="w-14 h-14 -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="3"
            className="text-gray-700" />
          <circle cx="18" cy="18" r="15.5" fill="none" strokeWidth="3"
            stroke={strokeColor}
            strokeDasharray={`${100 - score} ${score}`}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold"
          style={{ color: strokeColor }}>
          {100 - score}
        </span>
      </div>
      <div>
        <div className="text-sm font-bold">{label}</div>
        <div className="text-[10px]" style={{ color: 'var(--color-text-dim)' }}>{safetyLabel}</div>
      </div>
    </div>
  )
}

function RiskIcon({ level }: { level: string }) {
  const props = { className: 'w-5 h-5 shrink-0 mt-0.5' }
  switch (level) {
    case 'critical': return <TriangleAlert {...props} style={{ color: '#ef4444' }} />
    case 'high': return <AlertTriangle {...props} style={{ color: '#f97316' }} />
    case 'medium': return <AlertCircle {...props} style={{ color: '#eab308' }} />
    default: return <Info {...props} style={{ color: '#60a5fa' }} />
  }
}

export default function SafetyReport({ report }: SafetyReportProps) {
  const { t } = useT()
  if (!report) return null

  const hasIssues = report.total_issues > 0
  const isSafe = report.verdict === 'safe'
  const hasSecurityIssues = (report.security_issues ?? report.total_issues) > 0
  const hasQualityIssues = (report.quality_issues ?? 0) > 0
  const qualScore = report.quality_score ?? 0
  const showQuality = qualScore > 0 || hasQualityIssues

  return (
    <div className="space-y-4">
      {/* Verdict banner */}
      <div
        className={`rounded-2xl border p-4 ${
          isSafe
            ? 'border-emerald-500/20 bg-emerald-500/5'
            : report.verdict === 'dangerous'
            ? 'border-red-500/20 bg-red-500/5'
            : report.verdict === 'needs_review'
            ? 'border-orange-500/20 bg-orange-500/5'
            : 'border-yellow-500/20 bg-yellow-500/10'
        }`}
      >
        <div className="flex items-start gap-4 flex-wrap">
          <ScoreGauge score={report.score} label={t('safety.securityScore')} safetyLabel={t('safety.security')} />
          {showQuality && (
            <ScoreGauge score={qualScore} label={t('safety.qualityScore')} safetyLabel={t('safety.quality')} color="#8b5cf6" />
          )}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm mb-1">{report.verdict_label}</h3>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
              {report.verdict_description}
            </p>
            {report.simple_summary && (
              <p className="text-xs mt-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>
                {report.simple_summary}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* What this code does */}
      <div
        className="rounded-2xl border p-4"
        style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
      >
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Code className="w-4 h-4" />
          {t('safety.whatItDoes')}
        </h3>
        <ul className="space-y-1.5">
          {report.what_it_does.map((item, i) => (
            <li key={i} className="text-xs flex items-start gap-2" style={{ color: 'var(--color-text-muted)' }}>
              <span className="w-1 h-1 rounded-full bg-pink-400 mt-1.5 shrink-0" />
              {item}
            </li>
          ))}
        </ul>
        <div className="mt-3 text-[10px]" style={{ color: 'var(--color-text-dim)' }}>
          {t('safety.language')}: {report.language} · {report.scanned_lines} {t('safety.linesScanned')}
          {hasSecurityIssues && ` · ${report.security_issues ?? report.total_issues} security`}
          {showQuality && ` · ${report.quality_issues} quality`}
        </div>
      </div>

      {/* Security issues */}
      {hasSecurityIssues && (
        <div
          className="rounded-2xl border overflow-hidden"
          style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
        >
          <div className="px-4 py-3 border-b flex items-center justify-between"
            style={{ borderColor: 'var(--color-sub-border)' }}>
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              {t('safety.securityIssues') || 'Security Issues'}
            </h3>
            <div className="flex gap-2 text-[10px]">
              {Object.entries(report.finding_breakdown).filter(([level]) => level !== 'info').map(([level, count]) => (
                <span key={level} className={`px-2 py-0.5 rounded-full ${
                  level === 'critical' ? 'bg-red-500/10 text-red-400' :
                  level === 'high' ? 'bg-orange-500/10 text-orange-400' :
                  level === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                  'bg-blue-500/10 text-blue-400'
                }`}>
                  {count} {t('safety.' + level) || level}
                </span>
              ))}
            </div>
          </div>

          <div className="divide-y" style={{ borderColor: 'var(--color-sub-border)' }}>
            {report.findings.filter(f => f.finding_type !== 'quality').map((finding, idx) => (
              <FindingRow key={idx} finding={finding} />
            ))}
          </div>
        </div>
      )}

      {/* Code quality issues */}
      {showQuality && (
        <div
          className="rounded-2xl border overflow-hidden"
          style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
        >
          <div className="px-4 py-3 border-b flex items-center justify-between"
            style={{ borderColor: 'var(--color-sub-border)' }}>
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Gauge className="w-4 h-4" style={{ color: '#8b5cf6' }} />
              {t('safety.codeQuality') || 'Code Quality'}
            </h3>
            <div className="flex gap-2 text-[10px]">
              {report.quality_finding_breakdown && Object.entries(report.quality_finding_breakdown)
                .filter(([level]) => level !== 'info')
                .map(([level, count]) => (
                <span key={level} className={`px-2 py-0.5 rounded-full ${
                  level === 'critical' ? 'bg-red-500/10 text-red-400' :
                  level === 'high' ? 'bg-purple-500/10 text-purple-400' :
                  level === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                  'bg-blue-500/10 text-blue-400'
                }`}>
                  {count} {level}
                </span>
              ))}
            </div>
          </div>

          <div className="divide-y" style={{ borderColor: 'var(--color-sub-border)' }}>
            {(report.quality_findings ?? report.findings.filter(f => f.finding_type === 'quality')).map((finding, idx) => (
              <FindingRow key={idx} finding={finding} />
            ))}
          </div>
        </div>
      )}

      {/* No issues at all */}
      {!hasIssues && (
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center">
          <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
            style={{ backgroundColor: 'rgba(16,185,129,0.1)' }}>
            <ShieldCheck className="w-6 h-6" style={{ color: '#10b981' }} />
          </div>
          <h3 className="text-base font-semibold mb-1" style={{ color: '#10b981' }}>{t('safety.allClear')}</h3>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            {t('safety.noIssues')}
          </p>
        </div>
      )}
    </div>
  )
}

function FindingRow({ finding }: { finding: ScanFinding }) {
  const { t } = useT()
  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-3">
        <RiskIcon level={finding.risk_level} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-medium">{finding.title}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
              finding.risk_level === 'critical' ? 'bg-red-500/10 text-red-400' :
              finding.risk_level === 'high' ? 'bg-orange-500/10 text-orange-400' :
              finding.risk_level === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
              'bg-gray-500/10 text-gray-400'
            }`}>
              {finding.risk_label}
            </span>
            {finding.line_number && (
              <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-dim)' }}>
                {t('safety.line')} {finding.line_number}
              </span>
            )}
          </div>
          <p className="text-xs leading-relaxed mb-2" style={{ color: 'var(--color-text-muted)' }}>
            {finding.description}
          </p>
          {finding.snippet && (
            <pre className="text-[10px] font-mono p-2 rounded-lg mb-2 overflow-x-auto"
              style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text-dim)' }}>
              {finding.snippet}
            </pre>
          )}
          <div className="text-xs flex items-start gap-1.5" style={{ color: 'var(--color-accent)' }}>
            <Lightbulb className="w-3 h-3 mt-0.5 shrink-0" />
            {finding.recommendation}
          </div>
        </div>
      </div>
    </div>
  )
}
