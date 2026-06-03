import { useEffect, useState, useRef, useCallback } from 'react'
import PigLogo from './PigLogo'

const EMAIL = 'cjwd1234cjwd@163.com'

const FAQ_ITEMS = [
  { q: 'How is TruffleKit different from a linter?', a: 'Linters check syntax and style. TruffleKit checks what keeps you up at night: hardcoded secrets, SQL injection risks, SSL keys in repos, database files exposed to the web, Docker ports open to the world, and default admin passwords. It also gives you a prioritized action plan — not just a list.' },
  { q: 'Do I need a TruffleKit account to use the CLI?', a: 'No. The CLI is completely free and offline. Just pip install and run truffle scan .. No account, no API key, no cloud dependency.' },
  { q: 'How do I know I can trust the scan results?', a: 'Every rule is open source — check cli/rules/ on GitHub. Each result points to a specific line of code you can verify yourself. The scanner uses deterministic matching, not AI. No hallucinations, no black box.' },
  { q: 'Do you also have a web platform?', a: 'Yes. The same scanner powers our web platform, which adds team collaboration, an asset library, invite code management, and expert code review for teams that need more than just CLI.' },
  { q: 'What project types does it support?', a: 'Any project. It auto-detects Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, and more. It checks for cross-language issues like hardcoded secrets, git history leaks, Docker misconfigurations, and missing documentation.' },
  { q: 'Can I get a custom version for my team?', a: 'Yes. We offer private deployment with custom rules tailored to your stack and compliance requirements. Contact us for details.' },
]

// ── Scroll reveal hook ──
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
  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  return (
    <div className="min-h-screen bg-[#0D1117] text-white">
      {/* ── Navbar ── */}
      <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${scrolled ? 'bg-[#0D1117]/90 backdrop-blur-md border-b border-slate-800' : 'bg-transparent'}`}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <PigLogo size={32} />
            <span className="text-lg font-bold tracking-tight">
              Truffle<span className="text-pink-400">Kit</span>
            </span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">Features</a>
            <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">Pricing</a>
            <a href="#faq" className="text-sm text-slate-400 hover:text-white transition-colors hidden sm:block">FAQ</a>
            <button onClick={goToLogin} className="text-sm text-slate-400 hover:text-white transition-colors">
              Sign In
            </button>
            <button onClick={goToLogin}
              className="text-sm px-4 py-2 rounded-lg bg-pink-500 hover:bg-pink-400 text-white font-medium transition-colors">
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════════════════════════════════════════════════
         HERO
         ═══════════════════════════════════════════════════════════════════ */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-pink-500/5 blur-3xl pointer-events-none" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="flex justify-center mb-6 animate-[fadeIn_0.6s_ease-out]">
            <PigLogo size={72} />
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-tight mb-5 animate-[fadeIn_0.8s_ease-out]">
            Ship AI-Generated Code{' '}
            <span className="bg-gradient-to-r from-pink-400 to-indigo-400 bg-clip-text text-transparent">
              With Confidence
            </span>
          </h1>
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-[fadeIn_1s_ease-out]">
            Not sure if your project is safe to deploy? TruffleKit scans your codebase,{' '}
            <span className="text-white font-medium">prioritizes what needs your attention</span>,{' '}
            and tells you exactly where to look — so you check <span className="text-white font-medium">3 files instead of 300</span>.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap animate-[fadeIn_1.2s_ease-out]">
            <a href="https://github.com/trufflekit/truffle"
              className="px-8 py-3.5 rounded-xl bg-pink-500 hover:bg-pink-400 text-white font-semibold text-base transition-all shadow-lg shadow-pink-500/25 hover:scale-105 active:scale-95">
              Download CLI — It's Free
            </a>
            <a href="#features"
              className="px-8 py-3.5 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 font-semibold text-base transition-colors hover:scale-105 active:scale-95">
              How It Works
            </a>
            <button onClick={goToLogin}
              className="px-8 py-3.5 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 font-semibold text-base transition-colors hover:scale-105 active:scale-95">
              Web Platform
            </button>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
         STATS BAR
         ═══════════════════════════════════════════════════════════════════ */}
      <FadeInSection>
        <section className="py-12 px-6 border-t border-slate-800/60">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { number: '22', label: 'Security Rules' },
            { number: 'OWASP', label: 'Verified Standards' },
            { number: 'Zero', label: 'False Positives Guarantee' },
            { number: 'Free', label: 'CLI — No Account Needed' },
          ].map((s, i) => (
            <div key={i}>
              <div className="text-3xl md:text-4xl font-extrabold bg-gradient-to-br from-pink-400 to-indigo-400 bg-clip-text text-transparent">
                {s.number}
              </div>
              <div className="text-xs text-slate-500 mt-1 uppercase tracking-wider">{s.label}</div>
            </div>
          ))}
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         FEATURES */}
      <FadeInSection>
      <section id="features" className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">What You Get</h2>
          <p className="text-slate-400 text-center text-sm mb-14 max-w-xl mx-auto">
            A deterministic security scanner + a team collaboration layer — or just use the CLI on its own.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <svg className="w-8 h-8 text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                  </svg>
                ),
                title: 'CLI Scanner — 22 Rules',
                desc: 'Run truffle scan . on any project. Auto-detects language, scans for hardcoded secrets, SSL leaks, DB exposure, Docker misconfiguration, debug artifacts, and more. No account needed.',
              },
              {
                icon: (
                  <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ),
                title: 'Action Plan Mode',
                desc: 'Not just a list — --plan mode tells you "fix these 3 critical issues first, then these 5 medium ones, ignore the rest." Each finding includes the line number, code snippet, fix steps, and OWASP reference.',
              },
              {
                icon: (
                  <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                  </svg>
                ),
                title: 'Fix Tracking & Progress',
                desc: 'Run truffle fix . after fixing issues. Next scan hides them automatically. Track your fix rate over time. Perfect for solo devs or small teams doing pre-deployment audits.',
              },
              {
                icon: (
                  <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" />
                  </svg>
                ),
                title: 'Fully Transparent Rules',
                desc: 'Every scanning rule is open source and linked to OWASP / CVE standards. Run truffle explain SEC-001 to see why an issue matters, what the fix is, and how to verify it yourself.',
              },
              {
                icon: (
                  <svg className="w-8 h-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                  </svg>
                ),
                title: 'Web Platform (For Teams)',
                desc: 'Need more than CLI? The web platform adds team collaboration, feature request board with duplicate detection, AI code generation, and human expert code review. Invite your team with access codes.',
              },
              {
                icon: (
                  <svg className="w-8 h-8 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                  </svg>
                ),
                title: 'Private Deployment',
                desc: 'Self-host the entire platform on your own infrastructure. Custom security rules, custom templates, white-label options. Ideal for teams with compliance requirements or data sovereignty needs.',
              },
            ].map((f, i) => (
              <div key={i} className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-all group">
                <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">{f.icon}</div>
                <h3 className="text-lg font-semibold mb-3">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         SCANNER SHOWCASE */}
      <FadeInSection>
      <section id="faq" className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-[10px] uppercase tracking-widest text-pink-400 font-semibold">TruffleKit CLI in Action</span>
              <h2 className="text-3xl font-bold mt-3 mb-4">One Command. Instant Results.</h2>
              <p className="text-sm text-slate-400 leading-relaxed mb-6">
                Run <code className="text-pink-400 bg-slate-800 px-1.5 py-0.5 rounded">truffle scan . --plan</code> on any project.
                See exactly what's critical, what's safe to ignore, and{' '}
                <span className="text-white">where to start fixing</span>.
                No account, no cloud upload, no AI black box.
              </p>
              <ul className="space-y-2 text-sm text-slate-400">
                {[
                  '🔴 Scans for hardcoded API keys, passwords, and secrets',
                  '🟠 Detects SSL private keys and database files in your repo',
                  '🟡 Checks Docker config, CORS rules, and debug leftovers',
                  '🔵 Finds missing .gitignore rules, open file permissions',
                  '⚪ Reports accumulated TODOs and missing documentation',
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-0.5">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 font-mono text-xs leading-relaxed">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-slate-600 ml-2">🍄  truffle scan . --plan</span>
              </div>
              <div className="space-y-1.5">
                <div className="text-emerald-400">┌────────────────────────────────────────────────┐</div>
                <div className="text-emerald-400">│   🍄  TruffleKit  AI Code Audit  v0.1.0       │</div>
                <div className="text-emerald-400">└────────────────────────────────────────────────┘</div>
                <div className="text-slate-400">─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─</div>
                <div><span className="text-white">Project:</span> my-ai-app (Python, JavaScript) <span className="text-slate-500">42 files</span></div>
                <div><span className="text-white">Health:</span> <span className="text-yellow-400">B</span> (68/100)  <span className="text-slate-500">3 must-fix, 5 should-fix</span></div>
                <div className="text-slate-400">─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─</div>
                <div className="text-red-400">□ 1. 🔴 SEC-001  API Key 硬编码</div>
                <div className="text-slate-400 ml-3">config.py:42  →  os.getenv() 替代</div>
                <div className="text-orange-400">□ 2. 🟠 SEC-010  数据库暴露</div>
                <div className="text-slate-400 ml-3">data/app.db  → 移到 Web 根目录外</div>
                <div className="text-yellow-400">□ 3. 🟡 SEC-006  调试输出残留</div>
                <div className="text-slate-400 ml-3">main.py:88  → 删除 print()</div>
                <div className="text-slate-500 mt-2">3 items to fix ≈ 6 minutes  12 items auto-hidden</div>
              </div>
            </div>
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         HOW IT WORKS */}
      <FadeInSection>
      <section className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">How It Works</h2>
          <p className="text-slate-400 text-center text-sm mb-14 max-w-xl mx-auto">
            One command to scan. One report to act on. One fix cycle to ship with confidence.
          </p>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '1', title: 'Scan', desc: 'Run truffle scan . in your project directory. The scanner checks 22 rules across your entire codebase — secrets, config, dependencies, Docker, docs, and more. Takes under a second.' },
              { step: '2', title: 'Review Your Plan', desc: 'The CLI tells you exactly what needs attention: "3 critical issues to fix, 5 medium to consider, 9 info items to ignore." Each finding includes the file, line number, fix steps, and reference links.' },
              { step: '3', title: 'Fix & Ship', desc: 'Fix the critical issues, run truffle fix . to mark them done, then scan again. When you see all green (A grade), you\'re ready to ship with a clean audit trail.' },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-pink-500 to-indigo-500 flex items-center justify-center text-2xl font-bold mx-auto mb-5 shadow-lg shadow-pink-500/20">
                  {s.step}
                </div>
                <h3 className="text-lg font-semibold mb-3">{s.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed max-w-sm mx-auto">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         PRICING */}
      <FadeInSection>
      <section id="pricing" className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">Pricing</h2>
          <p className="text-slate-400 text-center text-sm mb-14 max-w-xl mx-auto">
            CLI is free forever. Web platform for teams. Private deployment for organizations.
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {/* CLI (Free) */}
            <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800">
              <h3 className="text-lg font-semibold mb-1">CLI</h3>
              <div className="text-3xl font-extrabold mb-4">$0</div>
              <p className="text-xs text-slate-500 mb-6">Free forever — no account needed</p>
              <ul className="space-y-3 text-sm text-slate-400 mb-8">
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> 22 deterministic security rules</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Action plan mode (--plan)</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Fix tracking (truffle fix)</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Open source rules (OWASP)</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> JSON output for CI</li>
              </ul>
              <code className="block text-center text-xs text-slate-500 bg-slate-800 py-2 px-3 rounded-lg">pip install trufflekit</code>
            </div>

            {/* Team (Web Platform) */}
            <div className="p-8 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-900/30 border border-pink-500/30 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-pink-500 text-[10px] font-semibold uppercase tracking-wider">
                Web Platform
              </div>
              <h3 className="text-lg font-semibold mb-1">Team</h3>
              <div className="text-3xl font-extrabold mb-4">$29</div>
              <p className="text-xs text-slate-500 mb-6">Per month — bring your own API key</p>
              <ul className="space-y-3 text-sm text-slate-400 mb-8">
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Everything in CLI</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Team collaboration (roles, invites)</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Feature request board + duplicate detection</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> AI code generation (multi-provider)</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Expert code review</li>
              </ul>
              <button onClick={goToLogin}
                className="w-full py-2.5 rounded-xl bg-pink-500 hover:bg-pink-400 text-white font-medium text-sm transition-colors">
                Sign Up
              </button>
            </div>

            {/* Private Deployment */}
            <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800">
              <h3 className="text-lg font-semibold mb-1">Private Deployment</h3>
              <div className="text-3xl font-extrabold mb-4">Custom</div>
              <p className="text-xs text-slate-500 mb-6">Self-hosted on your infrastructure</p>
              <ul className="space-y-3 text-sm text-slate-400 mb-8">
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Everything in Team</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Self-hosted deployment (Docker)</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Custom rules for your stack</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Custom templates</li>
                <li className="flex items-start gap-2"><span className="text-emerald-400 mt-0.5">✓</span> Priority support & SLA</li>
              </ul>
              <a href="#contact"
                className="w-full inline-block text-center py-2.5 rounded-xl border border-slate-700 text-slate-300 font-medium text-sm hover:border-slate-500 transition-colors">
                Contact Us
              </a>
            </div>
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         COLLABORATION / CONTACT */}
      <FadeInSection>
      <section id="contact" className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-3xl mx-auto text-center">
          <span className="text-[10px] uppercase tracking-widest text-pink-400 font-semibold">Get in Touch</span>
          <h2 className="text-3xl font-bold mt-3 mb-4">Let's Collaborate</h2>
          <p className="text-slate-400 text-sm mb-8 max-w-xl mx-auto leading-relaxed">
            Have a project idea, interested in integrating TruffleKit into your workflow, or
            just want to say hello? I'd love to hear from you.
          </p>
          <div className="flex flex-col items-center gap-4">
            <a href={`mailto:${EMAIL}`}
              className="inline-flex items-center gap-3 px-8 py-4 rounded-xl bg-slate-900 border border-slate-700 hover:border-pink-500/50 transition-all group">
              <svg className="w-5 h-5 text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
              <span className="text-lg font-semibold group-hover:text-pink-400 transition-colors">{EMAIL}</span>
            </a>
            <p className="text-xs text-slate-600">
              I typically respond within 24 hours.
            </p>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-6 text-left">
            {[
              {
                title: '💡 Partnership',
                desc: 'Interested in integrating TruffleKit into your product or platform? Let\'s explore partnership opportunities.',
              },
              {
                title: '🛠️ Custom Development',
                desc: 'Need custom features, self-hosted deployment, or white-label solutions? I can build exactly what you need.',
              },
              {
                title: '📝 Feedback',
                desc: 'Have suggestions, bug reports, or feature ideas? Your feedback shapes the future of TruffleKit.',
              },
            ].map((item, i) => (
              <div key={i} className="p-6 rounded-xl bg-slate-900/30 border border-slate-800">
                <h3 className="text-sm font-semibold mb-2">{item.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         FAQ */}
      <FadeInSection>
      <section className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">Frequently Asked Questions</h2>
          <p className="text-slate-400 text-center text-sm mb-14 max-w-xl mx-auto">
            Everything you need to know about TruffleKit.
          </p>
          <div className="space-y-3">
            {FAQ_ITEMS.map((item, i) => (
              <div key={i}
                className="rounded-xl border border-slate-800 overflow-hidden transition-all"
                style={{ backgroundColor: openFaq === i ? 'rgba(30,41,59,0.5)' : 'transparent' }}>
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-5 text-left text-sm font-medium hover:bg-slate-900/30 transition-colors">
                  <span>{item.q}</span>
                  <svg className={`w-4 h-4 shrink-0 ml-4 transition-transform ${openFaq === i ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-5 text-sm text-slate-400 leading-relaxed border-t border-slate-800 pt-4">
                    {item.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         CTA */}
      <FadeInSection>
      <section className="py-20 px-6 border-t border-slate-800/60">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-5">Ship With Confidence</h2>
          <p className="text-slate-400 mb-8 text-lg">Run a single command. Know where you stand. Fix what matters. Then ship — with an audit trail you can prove.</p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <code className="px-10 py-4 rounded-xl bg-slate-900 text-pink-400 font-mono text-lg border border-slate-700 select-all">pip install trufflekit</code>
            <a href="#features"
              className="px-10 py-4 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 font-semibold text-lg transition-colors">
              How It Works
            </a>
            <a href={`mailto:${EMAIL}`}
              className="px-10 py-4 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-300 font-semibold text-lg transition-colors">
              Contact Me
            </a>
          </div>
        </div>
      </section>
      </FadeInSection>

      {/* ═══════════════════════════════════════════════════════════════════
         SCROLL TO TOP
         ═══════════════════════════════════════════════════════════════════ */}
      {showBackToTop && (
        <button onClick={scrollToTop}
          className="fixed bottom-8 right-8 z-50 w-12 h-12 rounded-full bg-pink-500/90 hover:bg-pink-400 text-white shadow-lg shadow-pink-500/30 flex items-center justify-center transition-all hover:scale-110 active:scale-90 animate-[fadeIn_0.3s_ease-out]"
          aria-label="Scroll to top">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
          </svg>
        </button>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
         FOOTER */}
      <footer className="border-t border-slate-800/60">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="md:col-span-1">
              <div className="flex items-center gap-2.5 mb-4">
                <PigLogo size={28} />
                <span className="text-base font-bold tracking-tight">
                  Truffle<span className="text-pink-400">Kit</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed max-w-xs">
                AI 项目安全审查工具。告诉你要从哪里看起，而不是丢给你一个列表。
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">Product</h4>
              <ul className="space-y-2.5">
                <li><a href="#features" className="text-sm text-slate-500 hover:text-slate-300 transition-colors">Features</a></li>
                <li><a href="#pricing" className="text-sm text-slate-500 hover:text-slate-300 transition-colors">Pricing</a></li>
                <li><button onClick={goToLogin} className="text-sm text-slate-500 hover:text-slate-300 transition-colors">Sign In</button></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">Resources</h4>
              <ul className="space-y-2.5">
                <li><a href="https://github.com/trufflekit/truffle" className="text-sm text-slate-500 hover:text-slate-300 transition-colors">GitHub</a></li>
                <li><a href={`mailto:${EMAIL}`} className="text-sm text-slate-500 hover:text-slate-300 transition-colors">Support</a></li>
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">Contact</h4>
              <ul className="space-y-2.5">
                <li>
                  <a href={`mailto:${EMAIL}`}
                    className="text-sm text-slate-500 hover:text-pink-400 transition-colors">
                    {EMAIL}
                  </a>
                </li>
                <li>
                  <a href="#contact"
                    className="text-sm text-slate-500 hover:text-slate-300 transition-colors">
                    Collaboration
                  </a>
                </li>
              </ul>
              <div className="mt-4 pt-4 border-t border-slate-800">
                <a href={`mailto:${EMAIL}`}
                  className="inline-flex items-center gap-2 text-xs text-pink-400 hover:text-pink-300 transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                  </svg>
                  Send me an email
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-slate-800/60 py-6 px-6">
          <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-slate-600 text-xs">
              <PigLogo size={16} />
              <span>TruffleKit &copy; {new Date().getFullYear()}. All rights reserved.</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-600">
              <span>Built with ❤️ for small teams</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
