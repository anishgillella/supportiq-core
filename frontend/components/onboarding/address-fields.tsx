'use client'

import { UseFormRegister, FieldErrors } from 'react-hook-form'
import { motion } from 'framer-motion'
import { Input } from '@/components/ui/input'
import { AddressFormData } from '@/lib/validations'

interface AddressFieldsProps {
  register: UseFormRegister<AddressFormData>
  errors: FieldErrors<AddressFormData>
}

export function AddressFields({ register, errors }: AddressFieldsProps) {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: { opacity: 1, y: 0 },
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-4"
    >
      <motion.div variants={itemVariants}>
        <Input
          label="Street address"
          placeholder="123 Main Street"
          error={errors.street?.message}
          {...register('street')}
        />
      </motion.div>

      <div className="grid grid-cols-2 gap-4">
        <motion.div variants={itemVariants}>
          <Input
            label="City"
            placeholder="San Francisco"
            error={errors.city?.message}
            {...register('city')}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <Input
            label="State"
            placeholder="CA"
            error={errors.state?.message}
            {...register('state')}
          />
        </motion.div>
      </div>

      <motion.div variants={itemVariants}>
        <Input
          label="ZIP code"
          placeholder="94102"
          error={errors.zipCode?.message}
          {...register('zipCode')}
        />
      </motion.div>
    </motion.div>
  )
}
