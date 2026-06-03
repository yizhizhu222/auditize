import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, renderHook, act } from '@testing-library/react'
import { ThemeProvider, useTheme, type ThemePreset } from '../context/ThemeContext'

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear()
    // Clear any CSS variables set by previous tests
    document.documentElement.style.cssText = ''
  })

  it('provides default theme preset', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })
    expect(result.current.themePreset).toBe('nexus-default')
  })

  it('reads theme from localStorage', () => {
    localStorage.setItem('nexus-theme-preset', 'dracula')
    localStorage.setItem('nexus-theme-font', 'fira-code')
    localStorage.setItem('nexus-theme-size', '16')
    localStorage.setItem('nexus-theme-ligatures', 'true')

    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })
    expect(result.current.themePreset).toBe('dracula')
    expect(result.current.fontFamily).toBe('fira-code')
    expect(result.current.fontSize).toBe(16)
    expect(result.current.fontLigatures).toBe(true)
  })

  it('falls back to defaults when localStorage is empty', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })
    expect(result.current.fontFamily).toBe('jetbrains-mono')
    expect(result.current.fontSize).toBe(14)
    expect(result.current.fontLigatures).toBe(false)
  })

  it('sets theme preset and persists to localStorage', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })

    act(() => {
      result.current.setThemePreset('monokai')
    })

    expect(result.current.themePreset).toBe('monokai')
    expect(localStorage.getItem('nexus-theme-preset')).toBe('monokai')
  })

  it('sets font family and persists', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })

    act(() => {
      result.current.setFontFamily('jetbrains-mono')
    })

    expect(result.current.fontFamily).toBe('jetbrains-mono')
    expect(localStorage.getItem('nexus-theme-font')).toBe('jetbrains-mono')
  })

  it('sets font size and persists', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })

    act(() => {
      result.current.setFontSize(18)
    })

    expect(result.current.fontSize).toBe(18)
    expect(localStorage.getItem('nexus-theme-size')).toBe('18')
  })

  it('toggles font ligatures and persists', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })

    act(() => {
      result.current.setFontLigatures(true)
    })

    expect(result.current.fontLigatures).toBe(true)
    expect(localStorage.getItem('nexus-theme-ligatures')).toBe('true')
  })

  it('applies CSS variables to document root', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })

    const root = document.documentElement
    expect(root.style.getPropertyValue('--color-bg')).toBe('#0D1117')
    expect(root.style.getPropertyValue('--color-accent')).toBe('#F472B6')
    expect(root.style.getPropertyValue('--app-font-size')).toBe('14px')
    expect(root.style.getPropertyValue('--app-font-ligatures')).toBe('none')

    act(() => {
      result.current.setThemePreset('dracula')
    })

    expect(root.style.getPropertyValue('--color-bg')).toBe('#282A36')
    expect(root.style.getPropertyValue('--color-accent')).toBe('#BD93F9')
  })

  it('throws error when useTheme used outside provider', () => {
    expect(() => renderHook(() => useTheme())).toThrow(
      'useTheme must be used within ThemeProvider'
    )
  })

  it('renders children correctly', () => {
    render(
      <ThemeProvider>
        <div data-testid="child">Hello</div>
      </ThemeProvider>
    )
    expect(screen.getByTestId('child')).toHaveTextContent('Hello')
  })
})
