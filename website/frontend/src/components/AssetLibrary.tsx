import { useState } from 'react'
import { useT } from '../context/LanguageContext'

interface AssetLibraryProps {
  onBack?: () => void
}

export default function AssetLibrary({ onBack }: AssetLibraryProps) {
  const { t } = useT()

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-3 px-6 h-14">
          {onBack && (
            <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-[#1C2128]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <h1 className="text-base font-semibold">{t('assets.codeAssets')}</h1>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center" style={{ color: 'var(--color-text-dim)' }}>
          <p className="text-sm">{t('assets.noAssets')}</p>
          <p className="text-xs mt-2">Asset library with dedup — full implementation available upon purchase</p>
        </div>
      </div>
    </div>
  )
}
