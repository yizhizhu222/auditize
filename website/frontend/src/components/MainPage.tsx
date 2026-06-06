import { useState } from 'react'
import { Sparkles, ShieldCheck, Users } from 'lucide-react'
import { useT } from '../context/LanguageContext'

interface MainPageProps {
  onGenerate: (idea: string, language: string) => void
  generating: boolean
  onNavigate: (page: string) => void
}

const TEMPLATES = [
  { icon: 'Package', titleKey: 'template.inventory', descKey: 'template.inventoryDesc', prompt: 'Build an inventory management system...' },
  { icon: 'Contact', titleKey: 'template.crm', descKey: 'template.crmDesc', prompt: 'Build a CRM with contact management...' },
  { icon: 'BarChart3', titleKey: 'template.dashboard', descKey: 'template.dashboardDesc', prompt: 'Build a data dashboard with charts...' },
  { icon: 'Receipt', titleKey: 'template.expense', descKey: 'template.expenseDesc', prompt: 'Build an expense reimbursement system...' },
  { icon: 'Wrench', titleKey: 'template.ticket', descKey: 'template.ticketDesc', prompt: 'Build a ticket management system...' },
  { icon: 'CalendarCheck', titleKey: 'template.booking', descKey: 'template.bookingDesc', prompt: 'Build a room booking system...' },
]

const LANG_KEYS: Record<string, string> = { python: 'lang.python', javascript: 'lang.javascript', go: 'lang.go', cpp: 'lang.cpp' }
const SCAN_LANGUAGES = ['python', 'javascript', 'go', 'cpp']

export default function MainPage({ onGenerate, generating, onNavigate }: MainPageProps) {
  const { t } = useT()
  const [idea, setIdea] = useState('')
  const [language, setLanguage] = useState('python')

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8 lg:py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl lg:text-4xl font-bold mb-4">{t('main.heroTitle')}</h1>
          <p className="text-sm text-slate-400 max-w-2xl mx-auto">{t('main.heroDesc')}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
          {[
            { icon: Sparkles, title: t('main.value1Title'), desc: t('main.value1Desc') },
            { icon: ShieldCheck, title: t('main.value2Title'), desc: t('main.value2Desc') },
            { icon: Users, title: t('main.value3Title'), desc: t('main.value3Desc') },
          ].map(v => (
            <div key={v.title} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
              <v.icon className="w-4 h-4 mx-auto mb-2" style={{ color: 'var(--color-accent)' }} />
              <div className="text-sm font-semibold mb-1">{v.title}</div>
              <div className="text-[11px] text-slate-400">{v.desc}</div>
            </div>
          ))}
        </div>

        <div className="mb-6">
          <h2 className="text-sm font-semibold mb-3">{t('main.quickStart')}</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {TEMPLATES.map((tmpl, i) => (
              <button key={i} onClick={() => setIdea(tmpl.prompt)}
                className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-left text-xs hover:border-pink-500/30 transition-all">
                {t(tmpl.titleKey)}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-1">
          <textarea value={idea} onChange={e => setIdea(e.target.value)}
            placeholder={t('main.orDescribe')} rows={3}
            className="w-full bg-transparent resize-none px-4 py-3 text-sm text-white focus:outline-none rounded-2xl" />
          <div className="flex items-center justify-between px-1 pb-1 pt-2">
            <span className="text-[11px] text-slate-500">{t('main.language')}</span>
            <button disabled className="px-6 py-2.5 rounded-xl bg-pink-500 text-white text-sm font-semibold flex items-center gap-2 opacity-40 cursor-not-allowed">
              <Sparkles className="w-4 h-4" /> {t('main.generate')}
            </button>
          </div>
        </div>

        <div className="mt-6 text-xs text-center text-slate-500">
          AI Code Generation with SSE streaming + auto security scan — full implementation available upon purchase
        </div>
      </div>
    </div>
  )
}
