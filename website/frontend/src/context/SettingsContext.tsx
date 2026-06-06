import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface SettingsContextType {
  openAiKey: string; setOpenAiKey: (k: string) => void
  openRouterKey: string; setOpenRouterKey: (k: string) => void
  deepSeekKey: string; setDeepSeekKey: (k: string) => void
  anthropicKey: string; setAnthropicKey: (k: string) => void
  activeProvider: string; setActiveProvider: (p: string) => void
  activeModel: string; setActiveModel: (m: string) => void
  configuredProviders: string[]
  modelsByProvider: Record<string, any[]>
  modelsLoading: boolean
  loadSettingsFromBackend: () => Promise<void>
  reloadKeysFromStorage: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

function loadKeys(): Record<string, string> {
  const keys: Record<string, string> = {}
  const STORAGE_KEYS: Record<string, string> = {
    'OpenAI': 'nexus-settings-openai', 'OpenRouter': 'nexus-settings-openrouter',
    'DeepSeek': 'nexus-settings-deepseek', 'Anthropic': 'nexus-settings-anthropic',
  }
  for (const [provider, key] of Object.entries(STORAGE_KEYS)) {
    keys[provider] = localStorage.getItem(key) || ''
  }
  return keys
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const savedKeys = loadKeys()
  const [openAiKey, setOpenAiKey] = useState(savedKeys['OpenAI'])
  const [openRouterKey, setOpenRouterKey] = useState(savedKeys['OpenRouter'])
  const [deepSeekKey, setDeepSeekKey] = useState(savedKeys['DeepSeek'])
  const [anthropicKey, setAnthropicKey] = useState(savedKeys['Anthropic'])
  const [activeProvider, setActiveProvider] = useState('DeepSeek')
  const [activeModel, setActiveModel] = useState('deepseek-chat')
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, any[]>>({})
  const [modelsLoading, setModelsLoading] = useState(false)

  const configuredProviders = [openAiKey, openRouterKey, deepSeekKey, anthropicKey]
    .reduce<string[]>((acc, key, i) => {
      if (key) acc.push(Object.keys({ 'OpenAI': 1, 'OpenRouter': 1, 'DeepSeek': 1, 'Anthropic': 1 })[i])
      return acc
    }, [])

  const reloadKeysFromStorage = useCallback(() => {
    const keys = loadKeys()
    setOpenAiKey(keys['OpenAI']); setOpenRouterKey(keys['OpenRouter'])
    setDeepSeekKey(keys['DeepSeek']); setAnthropicKey(keys['Anthropic'])
  }, [])

  const loadSettingsFromBackend = useCallback(async () => {}, [])

  return (
    <SettingsContext.Provider value={{
      openAiKey, setOpenAiKey, openRouterKey, setOpenRouterKey,
      deepSeekKey, setDeepSeekKey, anthropicKey, setAnthropicKey,
      activeProvider, setActiveProvider, activeModel, setActiveModel,
      configuredProviders, modelsByProvider, modelsLoading,
      loadSettingsFromBackend, reloadKeysFromStorage,
    }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider')
  return ctx
}
