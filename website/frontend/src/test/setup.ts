import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Make fetch available globally in tests
declare global {
  var fetch: typeof globalThis.fetch
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false, media: query, onchange: null,
    addListener: () => {}, removeListener: () => {},
    addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
  }),
})
