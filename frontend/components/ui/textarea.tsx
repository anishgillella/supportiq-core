'use client'

import { forwardRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { AlertCircle } from 'lucide-react'

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  maxLength?: number
  showCount?: boolean
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, maxLength, showCount = true, value, ...props }, ref) => {
    const [isFocused, setIsFocused] = useState(false)
    const charCount = typeof value === 'string' ? value.length : 0

    return (
      <motion.div
        className="space-y-2"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {label && (
          <label className="block text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <div className="relative">
          <motion.div
            className="absolute inset-0 rounded-xl pointer-events-none"
            animate={{
              boxShadow: isFocused
                ? '0 0 0 2px rgba(139, 92, 246, 0.3), 0 0 20px rgba(139, 92, 246, 0.1)'
                : 'none',
            }}
            transition={{ duration: 0.2 }}
          />
          <textarea
            ref={ref}
            value={value}
            maxLength={maxLength}
            className={cn(
              'w-full px-4 py-3 rounded-xl min-h-[120px] resize-none',
              'bg-bg-elevated border border-border',
              'text-text-primary placeholder:text-text-muted',
              'transition-all duration-200',
              'focus:outline-none focus:border-accent-primary',
              error && 'border-error/50 focus:border-error',
              className
            )}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            {...props}
          />

          {/* Character count */}
          {showCount && maxLength && (
            <div className="absolute bottom-3 right-3 text-xs text-text-muted">
              <span className={cn(charCount > maxLength * 0.9 && 'text-error')}>
                {charCount}
              </span>
              /{maxLength}
            </div>
          )}
        </div>

        {/* Error message */}
        <AnimatePresence mode="wait">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -5, height: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-2 text-sm text-error"
            >
              <AlertCircle className="h-4 w-4" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    )
  }
)

Textarea.displayName = 'Textarea'

export { Textarea }
