'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import Link from 'next/link'
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
  const [emailExists, setEmailExists] = useState(false)
  const [checkingEmail, setCheckingEmail] = useState(false)
  const [scrapingStatus, setScrapingStatus] = useState<string | null>(null)

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
  const email = watch('email')

  // Debounced email check
  const checkEmailExists = useCallback(async (emailToCheck: string) => {
    if (!emailToCheck || emailToCheck.length < 5 || !emailToCheck.includes('@')) {
      setEmailExists(false)
      return
    }

    setCheckingEmail(true)
    try {
      const result = await api.checkEmail(emailToCheck)
      setEmailExists(result.exists)
    } catch {
      setEmailExists(false)
    } finally {
      setCheckingEmail(false)
    }
  }, [])

  // Check email when it changes (with debounce)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (email && !errors.email) {
        checkEmailExists(email)
      } else {
        setEmailExists(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [email, errors.email, checkEmailExists])

  // Redirect if already authenticated and past step 1
  useEffect(() => {
    if (token && currentStep > 1) {
      router.push(`/step-${currentStep}`)
    }
  }, [token, currentStep, router])

  const onSubmit = async (data: RegistrationFormData) => {
    setIsLoading(true)
    setError(null)
    setScrapingStatus(null)

    try {
      // Register user with company info
      const response = await api.register(
        data.email,
        data.password,
        data.companyName,
        data.companyWebsite
      )
      setAuth(response.user_id, response.access_token)
      updateFormData({ email: data.email })

      // Start knowledge base scraping in background
      setScrapingStatus('Setting up your knowledge base...')
      try {
        await api.scrapeWebsite(response.access_token, data.companyWebsite)
      } catch {
        // Don't fail registration if scraping fails
        console.warn('Website scraping failed, user can add documents later')
      }

      setStep(2)
      router.push('/step-2')
    } catch (err) {
      if (err instanceof Error && err.message.includes('already exists')) {
        try {
          const response = await api.login(data.email, data.password)
          setAuth(response.user_id, response.access_token)
          updateFormData({ email: data.email })

          const progress = await api.getProgress(response.access_token)
          if (progress.onboarding_completed) {
            router.push('/complete')
          } else {
            setStep(progress.current_step)
            router.push(progress.current_step === 1 ? '/step-2' : `/step-${progress.current_step}`)
          }
        } catch (loginErr) {
          setError('An account with this email already exists. Please use the correct password or try a different email.')
        }
      } else {
        setError(err instanceof Error ? err.message : 'Registration failed')
      }
    } finally {
      setIsLoading(false)
      setScrapingStatus(null)
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
                success={dirtyFields.email && !errors.email && !emailExists}
                {...register('email')}
              />
              {emailExists && !errors.email && (
                <motion.p
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-2 text-sm text-amber-500"
                >
                  An account with this email already exists.{' '}
                  <Link href="/login" className="text-accent-primary hover:underline font-medium">
                    Sign in instead
                  </Link>
                </motion.p>
              )}
              {checkingEmail && (
                <p className="mt-1 text-xs text-text-muted">Checking email...</p>
              )}
            </motion.div>

            <motion.div variants={itemVariants}>
              <Input
                label="Company name"
                type="text"
                placeholder="Acme Inc."
                error={errors.companyName?.message}
                success={dirtyFields.companyName && !errors.companyName}
                {...register('companyName')}
              />
            </motion.div>

            <motion.div variants={itemVariants}>
              <Input
                label="Company website"
                type="url"
                placeholder="https://example.com"
                error={errors.companyWebsite?.message}
                success={dirtyFields.companyWebsite && !errors.companyWebsite}
                hint="We'll analyze your website to build your AI knowledge base"
                {...register('companyWebsite')}
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

            {scrapingStatus && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 rounded-lg bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-sm flex items-center gap-2"
              >
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {scrapingStatus}
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
            disabled={!isValid || emailExists}
          >
            {isLoading ? 'Creating account...' : 'Continue'}
          </Button>

          <p className="text-sm text-text-muted text-center">
            Already have an account?{' '}
            <Link href="/login" className="text-accent-primary hover:underline">
              Sign in
            </Link>
          </p>

          <p className="text-xs text-text-muted text-center">
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
