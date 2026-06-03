import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

/* ── Types ── */

export type ThemePreset = 'terminal' | 'nexus-default' | 'dracula' | 'github-light' | 'monokai' | 'system'
export type FontFamily = 'system' | 'jetbrains-mono' | 'fira-code' | 'consolas'

interface ThemeContextType {
  themePreset: ThemePreset
  setThemePreset: (p: ThemePreset) => void
  fontFamily: FontFamily
  setFontFamily: (f: FontFamily) => void
  fontSize: number
  setFontSize: (s: number) => void
  fontLigatures: boolean
  setFontLigatures: (v: boolean) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

/* ── Storage keys ── */

const KEYS = {
  preset: 'nexus-theme-preset',
  font: 'nexus-theme-font',
  size: 'nexus-theme-size',
  ligatures: 'nexus-theme-ligatures',
}

/* ── Theme color maps ── */

const THEMES: Record<ThemePreset, Record<string, string>> = {
  'terminal': {
    '--color-bg': '#0A0A0A',
    '--color-panel': '#111111',
    '--color-border': '#1A1A1A',
    '--color-text': '#D0D0D0',
    '--color-text-muted': '#888888',
    '--color-text-dim': '#555555',
    '--color-hover': '#181818',
    '--color-sub-border': '#1A1A1A',
    '--color-accent': '#00FF41',
    '--color-accent-bg': 'rgba(0,255,65,0.06)',
  },
  'nexus-default': {
    '--color-bg': '#0D1117',
    '--color-panel': '#161B22',
    '--color-border': '#30363D',
    '--color-text': '#E6EDF3',
    '--color-text-muted': '#8D96A0',
    '--color-text-dim': '#484F58',
    '--color-hover': '#1C2128',
    '--color-sub-border': '#21262D',
    '--color-accent': '#F472B6',
    '--color-accent-bg': 'rgba(244,114,182,0.12)',
  },
  dracula: {
    '--color-bg': '#282A36',
    '--color-panel': '#343746',
    '--color-border': '#44475A',
    '--color-text': '#F8F8F2',
    '--color-text-muted': '#BD93F9',
    '--color-text-dim': '#6272A4',
    '--color-hover': '#3A3C4E',
    '--color-sub-border': '#44475A',
    '--color-accent': '#BD93F9',
    '--color-accent-bg': 'rgba(189,147,249,0.12)',
  },
  'github-light': {
    '--color-bg': '#F6F8FA',
    '--color-panel': '#FFFFFF',
    '--color-border': '#D0D7DE',
    '--color-text': '#1F2328',
    '--color-text-muted': '#656D76',
    '--color-text-dim': '#8C959F',
    '--color-hover': '#E8ECF0',
    '--color-sub-border': '#D8DEE4',
    '--color-accent': '#0969DA',
    '--color-accent-bg': 'rgba(9,105,218,0.08)',
  },
  monokai: {
    '--color-bg': '#1E1E1E',
    '--color-panel': '#252526',
    '--color-border': '#3C3C3C',
    '--color-text': '#D4D4D4',
    '--color-text-muted': '#A6E22E',
    '--color-text-dim': '#75715E',
    '--color-hover': '#2D2D2D',
    '--color-sub-border': '#3C3C3C',
    '--color-accent': '#A6E22E',
    '--color-accent-bg': 'rgba(166,226,46,0.12)',
  },
  system: {
    '--color-bg': '#0D1117',
    '--color-panel': '#161B22',
    '--color-border': '#30363D',
    '--color-text': '#E6EDF3',
    '--color-text-muted': '#8D96A0',
    '--color-text-dim': '#484F58',
    '--color-hover': '#1C2128',
    '--color-sub-border': '#21262D',
    '--color-accent': '#22D3EE',
    '--color-accent-bg': 'rgba(34,211,238,0.10)',
  },
}

/* ── Font family CSS values ── */

const FONTS: Record<FontFamily, string> = {
  system: 'Inter, system-ui, sans-serif',
  'jetbrains-mono': "'JetBrains Mono', 'Fira Code', monospace",
  'fira-code': "'Fira Code', 'JetBrains Mono', monospace",
  consolas: 'Consolas, "Courier New", monospace',
}

/* ── Provider ── */

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themePreset, setThemePreset] = useState<ThemePreset>(() => {
    const stored = localStorage.getItem(KEYS.preset) as ThemePreset | null
    return stored ?? 'nexus-default'
  })
  const [fontFamily, setFontFamily] = useState<FontFamily>(() => {
    const stored = localStorage.getItem(KEYS.font) as FontFamily | null
    return stored ?? 'jetbrains-mono'
  })
  const [fontSize, setFontSize] = useState(() => {
    const stored = localStorage.getItem(KEYS.size)
    const n = stored ? Number(stored) : NaN
    return Number.isFinite(n) ? n : 14
  })
  const [fontLigatures, setFontLigatures] = useState(() => {
    const stored = localStorage.getItem(KEYS.ligatures)
    return stored === 'true'
  })

  /* Resolve actual theme preset (for 'system', follow OS preference) */
  const resolveTheme = useCallback((preset: ThemePreset): ThemePreset => {
    if (preset !== 'system') return preset
    if (typeof window === 'undefined') return 'nexus-default'
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'github-light' : 'nexus-default'
  }, [])

  const [actualPreset, setActualPreset] = useState<ThemePreset>('nexus-default')

  /* Watch system theme when in 'system' mode */
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const handler = () => {
      if (themePreset === 'system') {
        setActualPreset(resolveTheme('system'))
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [themePreset, resolveTheme])

  /* Sync actualPreset when themePreset changes */
  useEffect(() => {
    setActualPreset(resolveTheme(themePreset))
  }, [themePreset, resolveTheme])

  /* Apply all theme variables to <html> */
  const applyTheme = useCallback(() => {
    const root = document.documentElement
    const colors = THEMES[actualPreset]

    for (const [key, val] of Object.entries(colors)) {
      root.style.setProperty(key, val)
    }

    root.style.setProperty('--app-font-family', FONTS[fontFamily])
    root.style.setProperty('--app-font-size', `${fontSize}px`)
    root.style.setProperty('--app-font-ligatures', fontLigatures ? 'normal' : 'none')
  }, [actualPreset, fontFamily, fontSize, fontLigatures])

  /* Persist and re-apply on change */
  useEffect(() => {
    localStorage.setItem(KEYS.preset, themePreset)
    localStorage.setItem(KEYS.font, fontFamily)
    localStorage.setItem(KEYS.size, String(fontSize))
    localStorage.setItem(KEYS.ligatures, String(fontLigatures))
    applyTheme()
  }, [themePreset, fontFamily, fontSize, fontLigatures, applyTheme])

  return (
    <ThemeContext.Provider
      value={{
        themePreset,
        setThemePreset,
        fontFamily,
        setFontFamily,
        fontSize,
        setFontSize,
        fontLigatures,
        setFontLigatures,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}