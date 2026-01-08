'use client'

import { UseFormRegister, FieldErrors } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Textarea } from '@/components/ui/textarea'

interface AboutMeFieldProps {
  register: UseFormRegister<{ aboutMe: string }>
  errors: FieldErrors<{ aboutMe: string }>
  value?: string
}

export function AboutMeField({ register, errors, value }: AboutMeFieldProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Textarea
        label="Tell us about yourself"
        placeholder="Share a bit about your background, role, and what you're hoping to achieve with SupportIQ..."
        error={errors.aboutMe?.message}
        maxLength={500}
        showCount
        value={value}
        {...register('aboutMe')}
      />
    </motion.div>
  )
}
