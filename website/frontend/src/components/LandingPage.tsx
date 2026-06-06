import { useState, useEffect, useRef, useCallback } from 'react'
import PigLogo from './PigLogo'

const FAQ_ITEMS = [
  { q: 'How is TruffleKit different from a linter?', a: 'Linters check syntax and style. TruffleKit checks secrets, SQL injection risks, SSL keys, and more.' },
  { q: 'Do I need a TruffleKit account to use the CLI?', a: 'No. The CLI is completely free and offline. Just pip install and run.' },
  { q: 'Can I get a custom version for my team?', a: 'Yes. We offer private deployment with custom rules tailored to your stack.' },
]

function useScrollReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.unobserve(el) } },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, visible }
}

function FadeInSection({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const { ref, visible } = useScrollReveal()
  return (
    <div ref={ref} className={`transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'} ${className}`}>
      {children}
    </div>
  )
}

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 40)
      setShowBackToTop(window.scrollY > 600)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const goToLogin = () => { window.location.pathname = '/login' }
  const scrollToTop = useCallback(() => { window.scrollTo({ top: 0, behavior: 'smooth' }) }, [])

  const FEATURES = [
    { title: 'CLI Scanner — 22 Rules', desc: 'Run truffle scan . on any project. No account needed.' },
    { title: 'Action Plan Mode', desc: 'Not just a list — --plan mode tells you what to fix first.' },
    { title: 'Fix Tracking', desc: 'Run truffle fix . after fixing. Track progress over time.' },
    { title: 'Transparent Rules', desc: 'Every rule is open source with OWASP references.' },
    { title: 'Web Platform', desc: 'Team collaboration, AI generation, and expert code review.' },
    { title: 'Private Deployment', desc: 'Self-host on your own infrastructure.' },
  ]

  const PRICING = [
    { name: 'CLI', price: '$0', desc: 'Free forever', features: ['22 security rules', 'Action plan mode', 'Fix tracking', 'CI-ready JSON'] },
    { name: 'Team', price: '$29', desc: 'Per month', features: ['Everything in CLI', 'Team collaboration', 'AI code generation', 'Expert review'] },
    { name: 'Private', price: 'Custom', desc: 'Self-hosted', features: ['Everything in Team', 'Self-hosted', 'Custom rules', 'Priority support'] },
  ]

  return (
    <div className="min-h-screen bg-[#0D1117] text-white">
      <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${scrolled ? 'bg-[#0D1117]/90 backdrop-blur-md border-b border-slate-800' : 'bg-transparent'}`}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <PigLogo size={32} />
            <span className="text-lg font-bold tracking-tight">Truffle<span className="text-pink-400">Kit</span></span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#features" className="text-sm text-slate-400 hover:text-white hidden sm:block">Features</a>
            <a href="#pricing" className="text-sm text-slate-400 hover:text-white hidden sm:block">Pricing</a>
            <button onClick={goToLogin} className="text-sm text-slate-400 hover:text-white">Sign In</button>
            <button onClick={goToLogin} className="text-sm px-4 py-2 rounded-lg bg-pink-500 hover:bg-pink-400 text-white font-medium">Get Started</button>
          </div>
        </div>
      </nav>

      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-pink-500/5 blur-3xl pointer-events-none" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="flex justify-center mb-6"><PigLogo size={72} /></div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-tight mb-5">
            Ship AI-Generated Code{' '}
            <span className="bg-gradient-to-r from-pink-400 to-indigo-400 bg-clip-text text-transparent">With Confidence</span>
          </h1>
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            Scan your codebase, prioritize what matters, and ship with confidence.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <a href="https://github.com/trufflekit/truffle" className="px-8 py-3.5 rounded-xl bg-pink-500 hover:bg-pink-400 text-white font-semibold">Download CLI — Free</a>
            <button onClick={goToLogin} className="px-8 py-3.5 rounded-xl border border-slate-700 text-slate-300 font-semibold">Web Platform</button>
          </div>
        </div>
      </section>

      <FadeInSection>
      <section id="features" className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">What You Get</h2>
          <p className="text-slate-400 text-center text-sm mb-14 max-w-xl mx-auto">
            A deterministic security scanner + a team collaboration layer.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => (
              <div key={i} className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800">
                <h3 className="text-lg font-semibold mb-3">{f.title}</h3>
                <p className="text-sm text-slate-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      <FadeInSection>
      <section id="pricing" className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-10">Pricing</h2>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {PRICING.map((p, i) => (
              <div key={i} className={`p-8 rounded-2xl ${i === 1 ? 'bg-gradient-to-b from-slate-900 to-slate-900/30 border border-pink-500/30' : 'bg-slate-900/50 border border-slate-800'}`}>
                <h3 className="text-lg font-semibold mb-1">{p.name}</h3>
                <div className="text-3xl font-extrabold mb-4">{p.price}</div>
                <p className="text-xs text-slate-500 mb-6">{p.desc}</p>
                <ul className="space-y-3 text-sm text-slate-400 mb-8">
                  {p.features.map((f, j) => <li key={j} className="flex items-start gap-2"><span className="text-emerald-400">✓</span> {f}</li>)}
                </ul>
                {i < 2 && <button onClick={goToLogin} className="w-full py-2.5 rounded-xl bg-pink-500 hover:bg-pink-400 text-white font-medium text-sm">Get Started</button>}
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      <FadeInSection>
      <section className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-10">FAQ</h2>
          <div className="space-y-3">
            {FAQ_ITEMS.map((item, i) => (
              <div key={i} className="rounded-xl border border-slate-800 overflow-hidden">
                <button onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-5 text-left text-sm font-medium">
                  <span>{item.q}</span>
                  <svg className={`w-4 h-4 shrink-0 ml-4 transition-transform ${openFaq === i ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>
                {openFaq === i && <div className="px-5 pb-5 text-sm text-slate-400 border-t border-slate-800 pt-4">{item.a}</div>}
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      <FadeInSection>
      <section className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-5">Ship With Confidence</h2>
          <code className="px-10 py-4 rounded-xl bg-slate-900 text-pink-400 font-mono text-lg border border-slate-700 select-all">pip install trufflekit</code>
        </div>
      </section>
      </FadeInSection>

      {showBackToTop && (
        <button onClick={scrollToTop} className="fixed bottom-8 right-8 z-50 w-12 h-12 rounded-full bg-pink-500/90 text-white shadow-lg flex items-center justify-center">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
          </svg>
        </button>
      )}

      <footer className="border-t border-slate-800/60 py-12 px-6">
        <div className="max-w-6xl mx-auto text-center text-xs text-slate-500">
          <PigLogo size={16} />
          <p className="mt-2">TruffleKit. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
