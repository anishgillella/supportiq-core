'use client'

import { forwardRef } from 'react'
import { motion, HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils'

interface CardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={cn(
          'rounded-2xl border border-border bg-bg-secondary p-6',
          className
        )}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        {...props}
      >
        {children}
      </motion.div>
    )
  }
)

Card.displayName = 'Card'

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

const CardHeader = ({ children, className }: CardHeaderProps) => (
  <div className={cn('mb-6', className)}>{children}</div>
)

interface CardTitleProps {
  children: React.ReactNode
  className?: string
}

const CardTitle = ({ children, className }: CardTitleProps) => (
  <h2 className={cn('text-2xl font-semibold text-text-primary', className)}>
    {children}
  </h2>
)

interface CardDescriptionProps {
  children: React.ReactNode
  className?: string
}

const CardDescription = ({ children, className }: CardDescriptionProps) => (
  <p className={cn('mt-2 text-text-secondary', className)}>{children}</p>
)

interface CardContentProps {
  children: React.ReactNode
  className?: string
}

const CardContent = ({ children, className }: CardContentProps) => (
  <div className={cn('space-y-4', className)}>{children}</div>
)

interface CardFooterProps {
  children: React.ReactNode
  className?: string
}

const CardFooter = ({ children, className }: CardFooterProps) => (
  <div className={cn('mt-6 flex items-center justify-between', className)}>
    {children}
  </div>
)

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }
