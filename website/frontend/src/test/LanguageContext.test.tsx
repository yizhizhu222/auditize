import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act, renderHook } from '@testing-library/react'
import { LanguageProvider, useT } from '../context/LanguageContext'

describe('LanguageContext', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to English', () => {
    const { result } = renderHook(() => useT(), { wrapper: LanguageProvider })
    expect(result.current.lang).toBe('en')
  })

  it('reads language from localStorage', () => {
    localStorage.setItem('nexus-language', 'zh')
    const { result } = renderHook(() => useT(), { wrapper: LanguageProvider })
    expect(result.current.lang).toBe('zh')
  })

  it('switches language and persists', () => {
    const { result } = renderHook(() => useT(), { wrapper: LanguageProvider })
    act(() => result.current.setLang('zh'))
    expect(result.current.lang).toBe('zh')
    expect(localStorage.getItem('nexus-language')).toBe('zh')
  })

  it('returns English translation for sidebar.team', () => {
    const { result } = renderHook(() => useT(), { wrapper: LanguageProvider })
    expect(result.current.t('sidebar.team')).toBe('Team')
  })

  it('returns Chinese translation after switching', () => {
    const { result } = renderHook(() => useT(), { wrapper: LanguageProvider })
    act(() => result.current.setLang('zh'))
    expect(result.current.t('sidebar.team')).toBe('团队')
    expect(result.current.t('sidebar.aiTools')).toBe('AI 工具')
    expect(result.current.t('main.generate')).toBe('生成代码')
  })

  it('falls back to English for missing translation keys', () => {
    const { result } = renderHook(() => useT(), { wrapper: LanguageProvider })
    act(() => result.current.setLang('zh'))
    // This key doesn't exist - should fallback to EN then to the key name
    const val = result.current.t('nonexistent.key.12345')
    expect(val).toBe('nonexistent.key.12345')
  })

  it('renders children correctly', () => {
    render(
      <LanguageProvider>
        <div data-testid="child">Hello</div>
      </LanguageProvider>
    )
    expect(screen.getByTestId('child')).toHaveTextContent('Hello')
  })

  it('throws error when useT used outside provider', () => {
    expect(() => renderHook(() => useT())).toThrow(
      'useT must be used within LanguageProvider'
    )
  })
})


