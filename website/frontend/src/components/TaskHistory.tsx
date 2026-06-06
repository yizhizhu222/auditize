import { useT } from '../context/LanguageContext'

interface TaskHistoryProps { onBack?: () => void }

export default function TaskHistory({ onBack }: TaskHistoryProps) {
  const { t } = useT()
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-3 px-6 h-14">
          {onBack && (
            <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-[#1C2128]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <h1 className="text-base font-semibold">{t('sidebar.history')}</h1>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>
          Task history — full implementation available upon purchase
        </p>
      </div>
    </div>
  )
}
