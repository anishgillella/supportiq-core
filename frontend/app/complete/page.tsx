'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { CheckCircle2, ArrowRight, Sparkles } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Confetti } from '@/components/onboarding/confetti'
import { useOnboardingStore } from '@/stores/onboarding-store'

export default function CompletePage() {
  const router = useRouter()
  const { formData, isCompleted, reset } = useOnboardingStore()
  const [showConfetti, setShowConfetti] = useState(false)

  useEffect(() => {
    // Trigger confetti after a short delay
    const timeout = setTimeout(() => setShowConfetti(true), 100)
    return () => clearTimeout(timeout)
  }, [])

  const handleStartOver = () => {
    reset()
    router.push('/')
  }

  const handleViewData = () => {
    router.push('/data')
  }

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center px-4">
      <Confetti trigger={showConfetti} />

      {/* Logo */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center gap-2 mb-8"
      >
        <div className="w-10 h-10 rounded-xl bg-accent-primary flex items-center justify-center">
          <span className="text-white font-bold text-lg">S</span>
        </div>
        <span className="text-xl font-semibold text-text-primary">SupportIQ</span>
      </motion.div>

      <Card className="max-w-md w-full">
        <CardContent className="pt-8 pb-6 text-center">
          {/* Success icon */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{
              type: 'spring',
              stiffness: 200,
              damping: 15,
              delay: 0.2,
            }}
            className="flex justify-center mb-6"
          >
            <div className="relative">
              <div className="w-20 h-20 rounded-full bg-success/20 flex items-center justify-center">
                <CheckCircle2 className="w-10 h-10 text-success" />
              </div>
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="absolute -top-2 -right-2"
              >
                <Sparkles className="w-6 h-6 text-accent-primary" />
              </motion.div>
            </div>
          </motion.div>

          {/* Welcome message */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h1 className="text-2xl font-bold text-text-primary mb-2">
              Welcome to SupportIQ!
            </h1>
            <p className="text-text-secondary mb-6">
              Your account is all set up and ready to go.
              {formData.email && (
                <span className="block mt-1 text-accent-primary">
                  {formData.email}
                </span>
              )}
            </p>
          </motion.div>

          {/* What's next section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="bg-bg-elevated rounded-xl p-4 mb-6"
          >
            <h3 className="text-sm font-medium text-text-secondary mb-3">
              What's next?
            </h3>
            <ul className="space-y-2 text-left">
              <li className="flex items-center gap-2 text-sm text-text-primary">
                <div className="w-5 h-5 rounded-full bg-accent-muted flex items-center justify-center">
                  <span className="text-xs text-accent-primary font-medium">1</span>
                </div>
                Connect your customer support channels
              </li>
              <li className="flex items-center gap-2 text-sm text-text-primary">
                <div className="w-5 h-5 rounded-full bg-accent-muted flex items-center justify-center">
                  <span className="text-xs text-accent-primary font-medium">2</span>
                </div>
                Configure your AI response templates
              </li>
              <li className="flex items-center gap-2 text-sm text-text-primary">
                <div className="w-5 h-5 rounded-full bg-accent-muted flex items-center justify-center">
                  <span className="text-xs text-accent-primary font-medium">3</span>
                </div>
                Start automating customer interactions
              </li>
            </ul>
          </motion.div>

          {/* Action buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="space-y-3"
          >
            <Button size="lg" className="w-full group" onClick={handleViewData}>
              View Your Data
              <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Button>
            <Button
              variant="ghost"
              size="lg"
              className="w-full"
              onClick={handleStartOver}
            >
              Start Over (Demo)
            </Button>
          </motion.div>
        </CardContent>
      </Card>

      {/* Footer */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="mt-8 text-sm text-text-muted"
      >
        Need help? Contact{' '}
        <a href="mailto:support@supportiq.com" className="text-accent-primary hover:underline">
          support@supportiq.com
        </a>
      </motion.p>
    </div>
  )
}
