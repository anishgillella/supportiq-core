'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from './sidebar'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'

interface AuthenticatedLayoutProps {
  children: React.ReactNode
}

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const router = useRouter()
  const { token, reset } = useOnboardingStore()
  const [isValidating, setIsValidating] = useState(true)

  useEffect(() => {
    if (!token) {
      router.push('/')
      return
    }

    // Validate token is still valid
    api.getCurrentUser(token)
      .then(() => {
        setIsValidating(false)
      })
      .catch(() => {
        // Token is invalid/expired, clear auth and redirect
        reset()
        router.push('/')
      })
  }, [token, router, reset])

  if (isValidating) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Sidebar />
      <main className="lg:ml-[260px] min-h-screen">
        {children}
      </main>
    </div>
  )
}
