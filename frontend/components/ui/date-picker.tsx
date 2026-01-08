'use client'

import { forwardRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Calendar, AlertCircle } from 'lucide-react'

interface DatePickerProps {
  label?: string
  error?: string
  value?: string
  onChange?: (value: string) => void
  className?: string
}

const DatePicker = forwardRef<HTMLInputElement, DatePickerProps>(
  ({ label, error, value, onChange, className }, ref) => {
    const [isFocused, setIsFocused] = useState(false)

    // Calculate max date (today minus 13 years for age restriction)
    const today = new Date()
    const maxDate = new Date(today.getFullYear() - 13, today.getMonth(), today.getDate())
      .toISOString()
      .split('T')[0]

    // Min date (reasonable limit of 120 years ago)
    const minDate = new Date(today.getFullYear() - 120, 0, 1)
      .toISOString()
      .split('T')[0]

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
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
            <Calendar className="h-5 w-5" />
          </div>
          <input
            ref={ref}
            type="date"
            value={value || ''}
            onChange={(e) => onChange?.(e.target.value)}
            min={minDate}
            max={maxDate}
            className={cn(
              'w-full pl-12 pr-4 py-3 rounded-xl',
              'bg-bg-elevated border border-border',
              'text-text-primary',
              'transition-all duration-200',
              'focus:outline-none focus:border-accent-primary',
              error && 'border-error/50 focus:border-error',
              '[&::-webkit-calendar-picker-indicator]:opacity-0',
              '[&::-webkit-calendar-picker-indicator]:absolute',
              '[&::-webkit-calendar-picker-indicator]:inset-0',
              '[&::-webkit-calendar-picker-indicator]:w-full',
              '[&::-webkit-calendar-picker-indicator]:h-full',
              '[&::-webkit-calendar-picker-indicator]:cursor-pointer',
              className
            )}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
          />
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

DatePicker.displayName = 'DatePicker'

export { DatePicker }
