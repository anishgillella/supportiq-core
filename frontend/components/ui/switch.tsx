'use client'

import { motion } from 'framer-motion'

interface SwitchProps {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  disabled?: boolean
  label?: string
  description?: string
}

export function Switch({ checked, onCheckedChange, disabled, label, description }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onCheckedChange(!checked)}
      className="flex items-start gap-3 text-left w-full"
    >
      <div
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full
          border-2 border-transparent transition-colors duration-200 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-accent-primary focus:ring-offset-2
          ${checked ? 'bg-accent-primary' : 'bg-gray-200 dark:bg-gray-700'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <motion.span
          initial={false}
          animate={{ x: checked ? 20 : 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full
            bg-white shadow ring-0 transition duration-200 ease-in-out
          `}
        />
      </div>
      {(label || description) && (
        <div className="flex flex-col">
          {label && (
            <span className={`text-sm font-medium ${disabled ? 'text-text-muted' : 'text-text-primary'}`}>
              {label}
            </span>
          )}
          {description && (
            <span className="text-xs text-text-muted mt-0.5">
              {description}
            </span>
          )}
        </div>
      )}
    </button>
  )
}
