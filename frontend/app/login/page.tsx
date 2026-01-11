'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const { setAuth, setStep, updateFormData, token, currentStep } = useOnboardingStore()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: 'onChange',
  })

  // Redirect if already authenticated
  useEffect(() => {
    if (token && currentStep > 1) {
      router.push(`/step-${currentStep}`)
    }
  }, [token, currentStep, router])

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    setError(null)

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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
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
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md"
      >
        <Card>
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>
              Sign in to continue your SupportIQ journey
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
                    {...register('email')}
                  />
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Input
                    label="Password"
                    type="password"
                    placeholder="Enter your password"
                    error={errors.password?.message}
                    {...register('password')}
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
                {isLoading ? 'Signing in...' : 'Sign In'}
              </Button>

              <p className="text-sm text-text-muted text-center">
                Don't have an account?{' '}
                <Link href="/" className="text-accent-primary hover:underline">
                  Create one
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </motion.div>
    </div>
  )
}
