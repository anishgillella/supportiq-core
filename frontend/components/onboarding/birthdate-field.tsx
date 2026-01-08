'use client'

import { motion } from 'framer-motion'
import { DatePicker } from '@/components/ui/date-picker'

interface BirthdateFieldProps {
  value?: string
  onChange: (value: string) => void
  error?: string
}

export function BirthdateField({ value, onChange, error }: BirthdateFieldProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <DatePicker
        label="Date of birth"
        value={value}
        onChange={onChange}
        error={error}
      />
      <p className="mt-2 text-sm text-text-muted">
        You must be at least 13 years old to use SupportIQ
      </p>
    </motion.div>
  )
}
