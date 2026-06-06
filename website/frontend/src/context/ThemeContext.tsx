import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

interface ThemeColors {
  bg: string; panel: string; border: string; text: string; textMuted: string; accent: string
}
interface ThemePreset { name: string; colors: ThemeColors; fontFamily?: string }
interface ThemeContextType {
  theme: string; setTheme: (t: string) => void
  fontFamily: string; setFontFamily: (f: string) => void
  fontSize: string; setFontSize: (f: string) => void
}

const STORAGE_KEY = 'nexus-theme'

const THEMES: Record<string, ThemePreset> = {
  terminal: {
    name: 'Terminal',
    colors: { bg: '#0A0A0A', panel: '#111111', border: '#1A1A1A', text: '#00FF41', textMuted: '#00CC33', accent: '#00FF41' },
    fontFamily: "'JetBrains Mono', monospace",
  },
  'nexus-default': {
    name: 'Nexus Dark',
    colors: { bg: '#0D1117', panel: '#161B22', border: '#30363D', text: '#E6EDF3', textMuted: '#8D96A0', accent: '#22D3EE' },
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
  },
  dracula: {
    name: 'Dracula',
    colors: { bg: '#282A36', panel: '#2D2F3E', border: '#414458', text: '#F8F8F2', textMuted: '#6272A4', accent: '#BD93F9' },
  },
  'github-light': {
    name: 'GitHub Light',
    colors: { bg: '#F6F8FA', panel: '#FFFFFF', border: '#D0D7DE', text: '#1F2328', textMuted: '#656D76', accent: '#0969DA' },
  },
  monokai: {
    name: 'Monokai',
    colors: { bg: '#1E1E1E', panel: '#252526', border: '#3E3E3E', text: '#F8F8F2', textMuted: '#888888', accent: '#A6E22E' },
  },
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState(() => localStorage.getItem(STORAGE_KEY) || 'nexus-default')
  const [fontFamily, setFontFamilyState] = useState(() => localStorage.getItem('nexus-font-family') || "'JetBrains Mono', monospace")
  const [fontSize, setFontSizeState] = useState(() => localStorage.getItem('nexus-font-size') || '13px')

  const applyTheme = useCallback((t: string) => {
    const preset = THEMES[t]
    if (!preset) return
    const root = document.documentElement
    const c = preset.colors
    root.style.setProperty('--color-bg', c.bg)
    root.style.setProperty('--color-panel', c.panel)
    root.style.setProperty('--color-border', c.border)
    root.style.setProperty('--color-text', c.text)
    root.style.setProperty('--color-text-muted', c.textMuted)
    root.style.setProperty('--color-accent', c.accent)
  }, [])

  const setTheme = useCallback((t: string) => {
    setThemeState(t); localStorage.setItem(STORAGE_KEY, t); applyTheme(t)
  }, [applyTheme])

  const setFontFamily = useCallback((f: string) => {
    setFontFamilyState(f); localStorage.setItem('nexus-font-family', f)
    document.documentElement.style.setProperty('--app-font-family', f)
  }, [])

  const setFontSize = useCallback((s: string) => {
    setFontSizeState(s); localStorage.setItem('nexus-font-size', s)
    document.documentElement.style.setProperty('--app-font-size', s)
  }, [])

  useEffect(() => { applyTheme(theme) }, [theme, applyTheme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, fontFamily, setFontFamily, fontSize, setFontSize }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
export { THEMES }
