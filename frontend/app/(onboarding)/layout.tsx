'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { usePathname } from 'next/navigation'
import { ProgressIndicator } from '@/components/onboarding/progress-indicator'
import { useOnboardingStore } from '@/stores/onboarding-store'

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const { currentStep } = useOnboardingStore()

  // Determine current step from pathname for visual indicator
  const getVisualStep = () => {
    if (pathname === '/') return 1
    if (pathname === '/step-2') return 2
    if (pathname === '/step-3') return 3
    return currentStep
  }

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col">
      {/* Header with logo and progress */}
      <header className="w-full py-6 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="flex items-center gap-2"
            >
              <div className="w-10 h-10 rounded-xl bg-accent-primary flex items-center justify-center">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span className="text-xl font-semibold text-text-primary">
                SupportIQ
              </span>
            </motion.div>
          </div>

          {/* Progress indicator */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <ProgressIndicator currentStep={getVisualStep()} totalSteps={3} />
          </motion.div>
        </div>
      </header>

      {/* Main content area */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 pb-12">
        <div className="w-full max-w-md">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, x: 20, filter: 'blur(10px)' }}
              animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, x: -20, filter: 'blur(10px)' }}
              transition={{
                duration: 0.3,
                ease: [0.25, 0.46, 0.45, 0.94],
              }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-text-muted text-sm">
        <p>© 2024 SupportIQ. All rights reserved.</p>
      </footer>
    </div>
  )
}
