const DEFAULT_TIMEOUT = 15000

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

export async function apiFetch<T = any>(
  url: string,
  options?: RequestInit,
  timeout = DEFAULT_TIMEOUT,
): Promise<ApiResult<T>> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    const data = await res.json()
    clearTimeout(timer)
    if (!res.ok) throw new ApiError(data?.detail || `HTTP ${res.status}`, res.status)
    return { ok: true, status: res.status, data }
  } catch (err: any) {
    clearTimeout(timer)
    if (err instanceof ApiError) throw err
    throw new Error('Network error')
  }
}
