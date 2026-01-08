'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { registrationSchema, RegistrationFormData } from '@/lib/validations'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'

export default function Step1Registration() {
  const router = useRouter()
  const { setAuth, setStep, updateFormData, token, currentStep } = useOnboardingStore()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, dirtyFields },
    watch,
  } = useForm<RegistrationFormData>({
    resolver: zodResolver(registrationSchema),
    mode: 'onChange',
  })

  const password = watch('password')

  // Redirect if already authenticated and past step 1
  useEffect(() => {
    if (token && currentStep > 1) {
      router.push(`/step-${currentStep}`)
    }
  }, [token, currentStep, router])

  const onSubmit = async (data: RegistrationFormData) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await api.register(data.email, data.password)
      setAuth(response.user_id, response.access_token)
      updateFormData({ email: data.email })
      setStep(2)
      router.push('/step-2')
    } catch (err) {
      // If user already exists, try to login
      if (err instanceof Error && err.message.includes('already exists')) {
        try {
          const response = await api.login(data.email, data.password)
          setAuth(response.user_id, response.access_token)
          updateFormData({ email: data.email })

          // Get current progress
          const progress = await api.getProgress(response.access_token)
          if (progress.onboarding_completed) {
            router.push('/complete')
          } else {
            setStep(progress.current_step)
            router.push(progress.current_step === 1 ? '/step-2' : `/step-${progress.current_step}`)
          }
        } catch (loginErr) {
          setError(loginErr instanceof Error ? loginErr.message : 'Login failed')
        }
      } else {
        setError(err instanceof Error ? err.message : 'Registration failed')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>
          Join SupportIQ and transform your customer service experience
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-4"
          >
            <motion.div variants={itemVariants}>
              <Input
                label="Email address"
                type="email"
                placeholder="you@company.com"
                error={errors.email?.message}
                success={dirtyFields.email && !errors.email}
                {...register('email')}
              />
            </motion.div>

            <motion.div variants={itemVariants}>
              <Input
                label="Password"
                type="password"
                placeholder="Create a strong password"
                error={errors.password?.message}
                success={dirtyFields.password && !errors.password}
                hint="At least 8 characters with uppercase, lowercase, and number"
                {...register('password')}
              />
            </motion.div>

            <motion.div variants={itemVariants}>
              <Input
                label="Confirm password"
                type="password"
                placeholder="Confirm your password"
                error={errors.confirmPassword?.message}
                success={
                  dirtyFields.confirmPassword &&
                  !errors.confirmPassword &&
                  password === watch('confirmPassword')
                }
                {...register('confirmPassword')}
              />
            </motion.div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm"
              >
                {error}
              </motion.div>
            )}
          </motion.div>
        </CardContent>

        <CardFooter className="flex-col gap-4">
          <Button
            type="submit"
            size="lg"
            className="w-full"
            isLoading={isLoading}
            disabled={!isValid}
          >
            {isLoading ? 'Creating account...' : 'Continue'}
          </Button>

          <p className="text-sm text-text-muted text-center">
            By continuing, you agree to our{' '}
            <a href="#" className="text-accent-primary hover:underline">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="#" className="text-accent-primary hover:underline">
              Privacy Policy
            </a>
          </p>
        </CardFooter>
      </form>
    </Card>
  )
}
