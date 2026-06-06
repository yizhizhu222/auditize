import { useState } from 'react'
import { useT } from '../context/LanguageContext'

interface TeamPageProps { onBack?: () => void }

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-400', approved: 'bg-blue-400', generating: 'bg-pink-400',
  completed: 'bg-emerald-400', rejected: 'bg-red-400', duplicate: 'bg-gray-400',
}
const statusLabelKeys: Record<string, string> = {
  pending: 'team.pending', approved: 'team.approve', rejected: 'team.reject', duplicate: 'team.markDuplicate',
}

function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const colors = ['from-pink-400 to-pink-500', 'from-cyan-400 to-blue-500', 'from-purple-400 to-violet-500']
  const idx = name.charCodeAt(0) % colors.length
  return (
    <div className={`rounded-xl bg-gradient-to-br ${colors[idx]} flex items-center justify-center text-white font-bold shrink-0`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}>
      {name.charAt(0).toUpperCase()}
    </div>
  )
}

export default function TeamPage({ onBack }: TeamPageProps) {
  const { t } = useT()
  const [activeTab, setActiveTab] = useState<'board' | 'members'>('board')

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="px-6 pt-6 pb-4">
          <h1 className="text-xl font-bold">{t('team.yourTeamWorkspace')}</h1>
        </div>
        <div className="flex gap-1 px-6 py-3">
          <button onClick={() => setActiveTab('board')}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === 'board' ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'
            }`}>{t('team.requestBoard')} (0)</button>
          <button onClick={() => setActiveTab('members')}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === 'members' ? 'text-pink-400 bg-pink-400/10' : 'text-[#484F58] hover:text-[#8D96A0]'
            }`}>{t('team.members')} (0)</button>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>{t('team.notSetUp')}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-dim)' }}>
            Team collaboration — full implementation available upon purchase
          </p>
        </div>
      </div>
    </div>
  )
}
