/**
 * Shared API utilities for Nexus AI frontend.
 *
 * Provides a timed fetch wrapper and auth helpers.
 */

const DEFAULT_TIMEOUT = 15_000 // 15s

// ── Auth helpers ────────────────────────────────────────────────────────────

export function authHeaders(): Record<string, string> {
  const t = localStorage.getItem('nexus-auth-token')
  return t
    ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' }
}

export function authToken(): string | null {
  return localStorage.getItem('nexus-auth-token')
}

export function authRole(): string {
  return localStorage.getItem('nexus-auth-role') || 'user'
}

// ── Timed fetch wrapper ────────────────────────────────────────────────────

export interface ApiResult<T = any> {
  ok: boolean
  status: number
  data: T
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Fetch with timeout, JSON parsing, and sensible error handling.
 * Throws ApiError on non-OK responses, or regular Error on network/timeout.
 */
export async function apiFetch<T = any>(
  url: string,
  options?: RequestInit,
  timeout = DEFAULT_TIMEOUT,
): Promise<ApiResult<T>> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    })

    let data: T
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      data = await res.json()
    } else {
      const text = await res.text()
      data = (res.ok ? text : { detail: text }) as unknown as T
    }

    if (!res.ok) {
      const detail = (data as any)?.detail || `HTTP ${res.status}`
      throw new ApiError(detail, res.status)
    }

    return { ok: true, status: res.status, data }
  } catch (err: any) {
    if (err instanceof ApiError) throw err
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. Please check your network connection.')
    }
    throw new Error('Cannot connect to server. Please check your network connection.')
  } finally {
    clearTimeout(timer)
  }
}
