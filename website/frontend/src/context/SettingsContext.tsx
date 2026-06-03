import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

/* ── Types ── */

export interface ModelInfo {
  id: string
  name: string
  provider: string
}

export interface ProviderConfig {
  id: string
  label: string
  hasKey: boolean
  defaultModel: string
}

interface SettingsContextType {
  openAiKey: string
  openRouterKey: string
  deepSeekKey: string
  anthropicKey: string
  customBaseUrl: string
  customApiKey: string
  ollamaUrl: string
  systemPrompt: string
  maxHistoryMessages: number
  activeModel: string
  activeProvider: string
  setOpenAiKey: (key: string) => void
  setOpenRouterKey: (key: string) => void
  setDeepSeekKey: (key: string) => void
  setAnthropicKey: (key: string) => void
  setCustomBaseUrl: (url: string) => void
  setCustomApiKey: (key: string) => void
  setOllamaUrl: (url: string) => void
  setSystemPrompt: (prompt: string) => void
  setMaxHistoryMessages: (n: number) => void
  setActiveModel: (model: string) => void
  setActiveProvider: (provider: string) => void
  configuredProviders: ProviderConfig[]
  availableModels: ModelInfo[]
  modelsByProvider: Record<string, ModelInfo[]>
  modelsLoading: boolean
  saveSettingsToBackend: () => Promise<void>
  loadSettingsFromBackend: () => Promise<void>
  refreshToken: () => Promise<void>
  reloadKeysFromStorage: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

const DEFAULT_SYSTEM_PROMPT =
  'You are an expert AI coding assistant. Generate clean, well-documented, secure code. Always follow best practices for the target language.'

const STORAGE_PREFIX = 'nexus-settings-'

/* ── Provider ── */

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [openAiKey, setOpenAiKey] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}openai`) ?? '')
  const [openRouterKey, setOpenRouterKey] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}openrouter`) ?? '')
  const [deepSeekKey, setDeepSeekKey] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}deepseek`) ?? '')
  const [anthropicKey, setAnthropicKey] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}anthropic`) ?? '')
  const [customBaseUrl, setCustomBaseUrl] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}custom_base_url`) ?? '')
  const [customApiKey, setCustomApiKey] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}custom_api_key`) ?? '')
  const [ollamaUrl, setOllamaUrl] = useState(() => {
    const stored = localStorage.getItem(`${STORAGE_PREFIX}ollama_url`)
    return (stored && stored !== 'http://localhost:11434') ? stored : ''
  })
  const [systemPrompt, setSystemPrompt] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}system_prompt`) ?? DEFAULT_SYSTEM_PROMPT)
  const [maxHistoryMessages, setMaxHistoryMessages] = useState(() => {
    const stored = localStorage.getItem(`${STORAGE_PREFIX}max_history`)
    const n = stored ? Number(stored) : NaN
    return Number.isFinite(n) ? n : 20
  })
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [activeModel, setActiveModel] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}active_model`) ?? '')
  const [activeProvider, setActiveProvider] = useState(() => localStorage.getItem(`${STORAGE_PREFIX}active_provider`) ?? '')

  /* ── Computed: which providers have keys ── */
  const configuredProviders: ProviderConfig[] = [
    { id: 'OpenAI',     label: 'OpenAI',     hasKey: !!openAiKey,       defaultModel: 'gpt-4o' },
    { id: 'OpenRouter', label: 'OpenRouter', hasKey: !!openRouterKey,   defaultModel: 'openai/gpt-4o' },
    { id: 'DeepSeek',   label: 'DeepSeek',   hasKey: !!deepSeekKey,     defaultModel: 'deepseek-v4-flash' },
    { id: 'Anthropic',  label: 'Anthropic',  hasKey: !!anthropicKey,    defaultModel: 'claude-sonnet-4-20250514' },
    { id: 'Custom',     label: 'Custom',     hasKey: !!customApiKey && !!customBaseUrl, defaultModel: '' },
  ].filter(p => p.hasKey)

  /* ── Computed: models grouped by provider ── */
  const modelsByProvider: Record<string, ModelInfo[]> = {}
  for (const m of availableModels) {
    if (!modelsByProvider[m.provider]) modelsByProvider[m.provider] = []
    modelsByProvider[m.provider].push(m)
  }

  /* ── Auto-select first configured provider if none selected ── */
  if (!activeProvider && configuredProviders.length > 0) {
    // Defer to next tick to avoid setState-during-render
    setTimeout(() => setActiveProvider(configuredProviders[0].id), 0)
  }
  /* ── Persist activeProvider ── */
  useEffect(() => { if (activeProvider) localStorage.setItem(`${STORAGE_PREFIX}active_provider`, activeProvider) }, [activeProvider])

  const authToken = () => localStorage.getItem('nexus-auth-token')

  const saveSettingsToBackend = useCallback(async (overrides?: Record<string, any>) => {
    const token = authToken()
    if (!token) return
    const body: Record<string, any> = overrides ?? {}
    // Fill in current state for any missing fields
    if (body.maxHistoryMessages === undefined) body.maxHistoryMessages = maxHistoryMessages
    if (body.openAiKey === undefined && openAiKey) body.openAiKey = openAiKey
    if (body.openRouterKey === undefined && openRouterKey) body.openRouterKey = openRouterKey
    if (body.deepSeekKey === undefined && deepSeekKey) body.deepSeekKey = deepSeekKey
    if (body.anthropicKey === undefined && anthropicKey) body.anthropicKey = anthropicKey
    if (body.customBaseUrl === undefined && customBaseUrl) body.customBaseUrl = customBaseUrl
    if (body.customApiKey === undefined && customApiKey) body.customApiKey = customApiKey
    if (body.ollamaUrl === undefined && ollamaUrl) body.ollamaUrl = ollamaUrl
    if (body.systemPrompt === undefined && systemPrompt) body.systemPrompt = systemPrompt
    if (body.activeModel === undefined && activeModel) body.activeModel = activeModel
    try {
      await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      })
    } catch (e) {
      console.warn('saveSettingsToBackend failed:', e)
    }
  }, [openAiKey, openRouterKey, deepSeekKey, anthropicKey, customBaseUrl, customApiKey, systemPrompt, maxHistoryMessages, activeModel])

  const loadSettingsFromBackend = useCallback(async () => {
    const token = authToken()
    if (!token) return
    try {
      const res = await fetch('/api/v1/settings', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return
      const data = await res.json()
      if (data.openAiKey) setOpenAiKey(data.openAiKey)
      if (data.openRouterKey) setOpenRouterKey(data.openRouterKey)
      if (data.deepSeekKey) setDeepSeekKey(data.deepSeekKey)
      if (data.anthropicKey) setAnthropicKey(data.anthropicKey)
      if (data.customBaseUrl) setCustomBaseUrl(data.customBaseUrl)
      if (data.customApiKey) setCustomApiKey(data.customApiKey)
      if (data.ollamaUrl) setOllamaUrl(data.ollamaUrl)
      if (data.systemPrompt) setSystemPrompt(data.systemPrompt)
      if (data.maxHistoryMessages !== undefined) setMaxHistoryMessages(data.maxHistoryMessages)
      if (data.activeModel) setActiveModel(data.activeModel)
    } catch (e) {
      console.warn('loadSettingsFromBackend failed:', e)
    }
  }, [])

  const refreshToken = async () => {
    const token = authToken()
    if (!token) return
    try {
      const res = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('nexus-auth-token', data.access_token)
      }
    } catch (e) {
      console.warn('refreshToken failed:', e)
    }
  }

  /* ── Concurrent model fetch from all configured providers ── */
  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    const fetchModels = async () => {
      setModelsLoading(true)
      const signal = controller.signal

      const tasks: Promise<{ provider: string; models: ModelInfo[] }>[] = []

      /* OpenRouter */
      if (openRouterKey) {
        tasks.push(
          (async () => {
            const res = await fetch('https://openrouter.ai/api/v1/models', { signal })
            if (!res.ok) throw new Error(`OpenRouter HTTP ${res.status}`)
            const json = await res.json()
            const list: ModelInfo[] = Array.isArray(json.data)
              ? json.data.map((m: { id: string; name?: string }) => ({
                  id: m.id,
                  name: m.name ?? m.id,
                  provider: 'OpenRouter',
                }))
              : []
            return { provider: 'OpenRouter', models: list }
          })(),
        )
      }

      /* DeepSeek */
      if (deepSeekKey) {
        tasks.push(
          (async () => {
            const res = await fetch('https://api.deepseek.com/models', {
              signal,
              headers: { Authorization: `Bearer ${deepSeekKey}` },
            })
            if (!res.ok) throw new Error(`DeepSeek HTTP ${res.status}`)
            const json = await res.json()
            const list: ModelInfo[] = Array.isArray(json.data)
              ? json.data.map((m: { id: string }) => ({
                  id: m.id,
                  name: m.id,
                  provider: 'DeepSeek',
                }))
              : []
            return { provider: 'DeepSeek', models: list }
          })(),
        )
      }

      /* Ollama (local) — only if user configured it */
      if (ollamaUrl && ollamaUrl !== 'http://localhost:11434') {
        const baseUrl = ollamaUrl.replace(/\/+$/, '')
        tasks.push(
          (async () => {
            try {
              const res = await fetch(`${baseUrl}/api/tags`, { signal })
              if (!res.ok) throw new Error(`Ollama HTTP ${res.status}`)
              const json = await res.json()
              const list: ModelInfo[] = Array.isArray(json.models)
                ? json.models.map((m: { name: string }) => ({ id: m.name, name: m.name, provider: 'Ollama' }))
                : []
              return { provider: 'Ollama', models: list }
            } catch {
              return { provider: 'Ollama', models: [] }
            }
          })(),
        )
      }

      /* Custom API (OpenAI-compatible) */
      if (customBaseUrl && customApiKey) {
        const base = customBaseUrl.replace(/\/+$/, '')
        const endpoints = [`${base}/models`, `${base}/v1/models`]

        tasks.push(
          (async () => {
            let lastErr: unknown
            for (const url of endpoints) {
              try {
                const res = await fetch(url, {
                  signal,
                  headers: { Authorization: `Bearer ${customApiKey}` },
                })
                if (!res.ok) continue
                const json = await res.json()
                const list: ModelInfo[] = Array.isArray(json.data)
                  ? json.data.map((m: { id: string; name?: string }) => ({
                      id: m.id,
                      name: m.name ?? m.id,
                      provider: new URL(customBaseUrl).hostname,
                    }))
                  : []
                return { provider: new URL(customBaseUrl).hostname, models: list }
              } catch (e) {
                lastErr = e
              }
            }
            throw lastErr ?? new Error('Custom API unreachable')
          })(),
        )
      }

      /* No providers configured */
      if (tasks.length === 0) {
        if (!cancelled) {
          setAvailableModels([])
          setModelsLoading(false)
        }
        return
      }

      const results = await Promise.allSettled(tasks)
      if (cancelled) return

      const merged = new Map<string, ModelInfo>()
      for (const result of results) {
        if (result.status === 'fulfilled') {
          for (const m of result.value.models) {
            /* Dedup by id — first provider wins */
            if (!merged.has(m.id)) {
              merged.set(m.id, m)
            }
          }
        } else {
          console.warn('Model fetch failed:', result.reason)
        }
      }

      setAvailableModels(Array.from(merged.values()))
      setModelsLoading(false)
    }

    fetchModels()
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [openRouterKey, deepSeekKey, customBaseUrl, customApiKey])

  /* Persist settings to localStorage */
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}openai`, openAiKey) }, [openAiKey])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}openrouter`, openRouterKey) }, [openRouterKey])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}deepseek`, deepSeekKey) }, [deepSeekKey])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}anthropic`, anthropicKey) }, [anthropicKey])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}custom_base_url`, customBaseUrl) }, [customBaseUrl])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}custom_api_key`, customApiKey) }, [customApiKey])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}ollama_url`, ollamaUrl) }, [ollamaUrl])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}system_prompt`, systemPrompt) }, [systemPrompt])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}max_history`, String(maxHistoryMessages)) }, [maxHistoryMessages])
  useEffect(() => { localStorage.setItem(`${STORAGE_PREFIX}active_model`, activeModel) }, [activeModel])

  return (
    <SettingsContext.Provider
      value={{
        openAiKey,
        openRouterKey,
        deepSeekKey,
        anthropicKey,
        customBaseUrl,
        customApiKey,
        systemPrompt,
        maxHistoryMessages,
        activeModel,
        activeProvider,
        setOpenAiKey,
        setOpenRouterKey,
        setDeepSeekKey,
        setAnthropicKey,
        setCustomBaseUrl,
        setCustomApiKey,
        setSystemPrompt,
        setMaxHistoryMessages,
        setActiveModel,
        setActiveProvider,
        ollamaUrl,
        setOllamaUrl,
        availableModels,
        modelsByProvider,
        configuredProviders,
        modelsLoading,
        saveSettingsToBackend,
        loadSettingsFromBackend,
        refreshToken,
      reloadKeysFromStorage: () => {
        const prefix = STORAGE_PREFIX
        setOpenAiKey(localStorage.getItem(`${prefix}openai`) ?? '')
        setOpenRouterKey(localStorage.getItem(`${prefix}openrouter`) ?? '')
        setDeepSeekKey(localStorage.getItem(`${prefix}deepseek`) ?? '')
        setAnthropicKey(localStorage.getItem(`${prefix}anthropic`) ?? '')
        setCustomBaseUrl(localStorage.getItem(`${prefix}custom_base_url`) ?? '')
        setCustomApiKey(localStorage.getItem(`${prefix}custom_api_key`) ?? '')
      },
      }}
    >
      {children}
    </SettingsContext.Provider>
  )
}

/* ── Hook ── */

export function useSettings() {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider')
  return ctx
}