'use client'

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Check, User, FileText, Sparkles } from 'lucide-react'

interface Step {
  label: string
  icon: React.ReactNode
}

interface ProgressIndicatorProps {
  currentStep: number
  totalSteps: number
}

const steps: Step[] = [
  { label: 'Account', icon: <User className="h-5 w-5" /> },
  { label: 'Profile', icon: <FileText className="h-5 w-5" /> },
  { label: 'Details', icon: <Sparkles className="h-5 w-5" /> },
]

export function ProgressIndicator({ currentStep, totalSteps }: ProgressIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2 sm:gap-4">
      {steps.slice(0, totalSteps).map((step, index) => {
        const stepNumber = index + 1
        const isCompleted = stepNumber < currentStep
        const isCurrent = stepNumber === currentStep

        return (
          <div key={index} className="flex items-center">
            {/* Step circle */}
            <div className="flex flex-col items-center">
              <motion.div
                className={cn(
                  'relative flex items-center justify-center w-12 h-12 rounded-full',
                  'border-2 transition-colors duration-300',
                  isCompleted && 'bg-accent-primary border-accent-primary',
                  isCurrent && 'border-accent-primary bg-accent-muted',
                  !isCompleted && !isCurrent && 'border-border bg-transparent'
                )}
                initial={false}
                animate={{
                  scale: isCurrent ? 1.05 : 1,
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                {isCompleted ? (
                  <motion.div
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  >
                    <Check className="h-5 w-5 text-white" strokeWidth={3} />
                  </motion.div>
                ) : (
                  <span
                    className={cn(
                      isCurrent ? 'text-accent-primary' : 'text-text-muted'
                    )}
                  >
                    {step.icon}
                  </span>
                )}

                {/* Pulse effect for current step */}
                {isCurrent && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-accent-primary"
                    animate={{
                      scale: [1, 1.2, 1],
                      opacity: [0.5, 0, 0.5],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                )}
              </motion.div>

              {/* Step label */}
              <span
                className={cn(
                  'mt-2 text-xs font-medium',
                  isCurrent ? 'text-accent-primary' : 'text-text-muted'
                )}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {index < totalSteps - 1 && (
              <div className="w-8 sm:w-16 h-0.5 mx-2 bg-border overflow-hidden -mt-6">
                <motion.div
                  className="h-full bg-accent-primary"
                  initial={{ width: '0%' }}
                  animate={{
                    width: stepNumber < currentStep ? '100%' : '0%',
                  }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
