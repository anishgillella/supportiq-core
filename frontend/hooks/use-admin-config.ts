'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

export type ComponentType = 'aboutMe' | 'address' | 'birthdate'

interface AdminConfig {
  page2: ComponentType[]
  page3: ComponentType[]
}

const DEFAULT_CONFIG: AdminConfig = {
  page2: ['aboutMe', 'address'],
  page3: ['birthdate'],
}

export function useAdminConfig() {
  const [config, setConfig] = useState<AdminConfig>(DEFAULT_CONFIG)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchConfig() {
      try {
        const data = await api.getConfig()
        setConfig({
          page2: data.page2 as ComponentType[],
          page3: data.page3 as ComponentType[],
        })
      } catch (err) {
        // Use default config if API fails
        console.warn('Failed to fetch admin config, using defaults:', err)
        setConfig(DEFAULT_CONFIG)
      } finally {
        setIsLoading(false)
      }
    }

    fetchConfig()
  }, [])

  const updateConfig = async (newConfig: AdminConfig) => {
    setError(null)
    try {
      await api.updateConfig(newConfig)
      setConfig(newConfig)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update config')
      return false
    }
  }

  return { config, isLoading, error, updateConfig }
}
