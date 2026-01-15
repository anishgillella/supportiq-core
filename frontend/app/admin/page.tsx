'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Settings, User, MapPin, Calendar, GripVertical, Check, AlertCircle } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useAdminConfig, ComponentType } from '@/hooks/use-admin-config'
import { PublicLayout } from '@/components/layout/public-layout'

interface ComponentOption {
  id: ComponentType
  label: string
  description: string
  icon: React.ReactNode
}

const COMPONENTS: ComponentOption[] = [
  {
    id: 'aboutMe',
    label: 'About Me',
    description: 'Large text area for user bio',
    icon: <User className="w-5 h-5" />,
  },
  {
    id: 'address',
    label: 'Address',
    description: 'Street, city, state, and ZIP',
    icon: <MapPin className="w-5 h-5" />,
  },
  {
    id: 'birthdate',
    label: 'Birthdate',
    description: 'Date picker with age validation',
    icon: <Calendar className="w-5 h-5" />,
  },
]

export default function AdminPage() {
  const { config, isLoading, error, updateConfig } = useAdminConfig()
  const [page2Components, setPage2Components] = useState<ComponentType[]>([])
  const [page3Components, setPage3Components] = useState<ComponentType[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Initialize from config
  useEffect(() => {
    if (!isLoading) {
      setPage2Components(config.page2)
      setPage3Components(config.page3)
    }
  }, [config, isLoading])

  const isComponentUsed = (id: ComponentType) => {
    return page2Components.includes(id) || page3Components.includes(id)
  }

  const toggleComponent = (page: 2 | 3, id: ComponentType) => {
    const currentPage = page === 2 ? page2Components : page3Components
    const setCurrentPage = page === 2 ? setPage2Components : setPage3Components
    const otherPage = page === 2 ? page3Components : page2Components
    const setOtherPage = page === 2 ? setPage3Components : setPage2Components

    if (currentPage.includes(id)) {
      // Prevent removing if page will have 0 components - show warning
      if (currentPage.length <= 1) {
        setSaveError(`Page ${page} must have at least one component`)
        setTimeout(() => setSaveError(null), 3000)
        return
      }
      setCurrentPage(currentPage.filter((c) => c !== id))
    } else {
      // Only add if total per page <= 2
      if (currentPage.length < 2) {
        // Remove from other page if it was there (but check it won't leave that page empty)
        if (otherPage.includes(id)) {
          if (otherPage.length <= 1) {
            setSaveError(`Cannot move: Page ${page === 2 ? 3 : 2} must have at least one component`)
            setTimeout(() => setSaveError(null), 3000)
            return
          }
          setOtherPage(otherPage.filter((c) => c !== id))
        }
        setCurrentPage([...currentPage, id])
      }
    }
    setSaveSuccess(false)
    setSaveError(null)
  }

  const handleSave = async () => {
    // Validate: each page must have at least 1 component
    if (page2Components.length === 0 || page3Components.length === 0) {
      setSaveError('Each page must have at least one component')
      return
    }

    setIsSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    const success = await updateConfig({
      page2: page2Components,
      page3: page3Components,
    })

    setIsSaving(false)
    if (success) {
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } else {
      setSaveError('Failed to save configuration')
    }
  }

  if (isLoading) {
    return (
      <PublicLayout>
        <div className="min-h-screen bg-bg-primary flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
        </div>
      </PublicLayout>
    )
  }

  return (
    <PublicLayout>
      <div className="min-h-screen bg-bg-primary py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-accent-primary flex items-center justify-center">
              <Settings className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-text-primary">Admin Panel</h1>
          </div>
          <p className="text-text-secondary">
            Configure which components appear on each onboarding page
          </p>
        </motion.div>

        {/* Available components */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Available Components
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {COMPONENTS.map((component) => (
              <div
                key={component.id}
                className={cn(
                  'p-4 rounded-xl border bg-bg-secondary transition-colors',
                  isComponentUsed(component.id)
                    ? 'border-accent-primary/50'
                    : 'border-border'
                )}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'w-10 h-10 rounded-lg flex items-center justify-center',
                      isComponentUsed(component.id)
                        ? 'bg-accent-primary/20 text-accent-primary'
                        : 'bg-bg-elevated text-text-muted'
                    )}
                  >
                    {component.icon}
                  </div>
                  <div>
                    <h3 className="font-medium text-text-primary">
                      {component.label}
                    </h3>
                    <p className="text-xs text-text-muted">{component.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Page configuration */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Page 2 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Page 2 Components</CardTitle>
                <CardDescription>
                  Select 1-2 components for the second page
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {COMPONENTS.map((component) => {
                    const isSelected = page2Components.includes(component.id)
                    const isOnOtherPage = page3Components.includes(component.id)

                    return (
                      <button
                        key={component.id}
                        onClick={() => toggleComponent(2, component.id)}
                        disabled={
                          (!isSelected && page2Components.length >= 2) ||
                          (!isSelected && isOnOtherPage && page3Components.length <= 1)
                        }
                        className={cn(
                          'w-full p-3 rounded-xl border flex items-center gap-3 transition-all',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                          isSelected
                            ? 'border-accent-primary bg-accent-primary/10'
                            : 'border-border hover:border-text-muted bg-bg-elevated'
                        )}
                      >
                        <div
                          className={cn(
                            'w-8 h-8 rounded-lg flex items-center justify-center',
                            isSelected
                              ? 'bg-accent-primary text-white'
                              : 'bg-bg-secondary text-text-muted'
                          )}
                        >
                          {component.icon}
                        </div>
                        <span
                          className={cn(
                            'font-medium',
                            isSelected ? 'text-accent-primary' : 'text-text-secondary'
                          )}
                        >
                          {component.label}
                        </span>
                        {isSelected && (
                          <Check className="w-4 h-4 ml-auto text-accent-primary" />
                        )}
                      </button>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Page 3 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Page 3 Components</CardTitle>
                <CardDescription>
                  Select 1-2 components for the third page
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {COMPONENTS.map((component) => {
                    const isSelected = page3Components.includes(component.id)
                    const isOnOtherPage = page2Components.includes(component.id)

                    return (
                      <button
                        key={component.id}
                        onClick={() => toggleComponent(3, component.id)}
                        disabled={
                          (!isSelected && page3Components.length >= 2) ||
                          (!isSelected && isOnOtherPage && page2Components.length <= 1)
                        }
                        className={cn(
                          'w-full p-3 rounded-xl border flex items-center gap-3 transition-all',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                          isSelected
                            ? 'border-accent-primary bg-accent-primary/10'
                            : 'border-border hover:border-text-muted bg-bg-elevated'
                        )}
                      >
                        <div
                          className={cn(
                            'w-8 h-8 rounded-lg flex items-center justify-center',
                            isSelected
                              ? 'bg-accent-primary text-white'
                              : 'bg-bg-secondary text-text-muted'
                          )}
                        >
                          {component.icon}
                        </div>
                        <span
                          className={cn(
                            'font-medium',
                            isSelected ? 'text-accent-primary' : 'text-text-secondary'
                          )}
                        >
                          {component.label}
                        </span>
                        {isSelected && (
                          <Check className="w-4 h-4 ml-auto text-accent-primary" />
                        )}
                      </button>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Save button and status */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-bg-secondary border border-border"
        >
          <div className="flex items-center gap-2">
            <AnimatePresence mode="wait">
              {saveSuccess && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="flex items-center gap-2 text-success"
                >
                  <Check className="w-4 h-4" />
                  <span className="text-sm">Configuration saved!</span>
                </motion.div>
              )}
              {saveError && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="flex items-center gap-2 text-error"
                >
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm">{saveError}</span>
                </motion.div>
              )}
              {!saveSuccess && !saveError && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-sm text-text-muted"
                >
                  Changes will apply to new users immediately
                </motion.span>
              )}
            </AnimatePresence>
          </div>
          <Button onClick={handleSave} isLoading={isSaving}>
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </motion.div>

        {/* Navigation links */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-8 flex justify-center gap-4 text-sm"
        >
          <a href="/" className="text-accent-primary hover:underline">
            View Onboarding →
          </a>
          <a href="/data" className="text-accent-primary hover:underline">
            View Data Table →
          </a>
        </motion.div>
      </div>
    </div>
    </PublicLayout>
  )
}
