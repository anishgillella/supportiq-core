'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AboutMeField } from '@/components/onboarding/about-me-field'
import { AddressFields } from '@/components/onboarding/address-fields'
import { BirthdateField } from '@/components/onboarding/birthdate-field'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { useAdminConfig, ComponentType } from '@/hooks/use-admin-config'
import { aboutMeSchema, addressSchema, birthdateSchema } from '@/lib/validations'
import { api } from '@/lib/api'

// Build dynamic schema based on components
function buildSchema(components: ComponentType[]) {
  const schemaObj: Record<string, z.ZodTypeAny> = {}

  components.forEach((comp) => {
    if (comp === 'aboutMe') {
      schemaObj.aboutMe = aboutMeSchema.shape.aboutMe
    } else if (comp === 'address') {
      Object.assign(schemaObj, addressSchema.shape)
    } else if (comp === 'birthdate') {
      schemaObj.birthdate = birthdateSchema.shape.birthdate
    }
  })

  return z.object(schemaObj)
}

export default function Step2Page() {
  const router = useRouter()
  const { token, currentStep, setStep, updateFormData, formData, completeOnboarding } = useOnboardingStore()
  const { config, isLoading: configLoading } = useAdminConfig()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const components = config.page2

  const schema = buildSchema(components)
  type FormData = z.infer<typeof schema>

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    setValue,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: {
      aboutMe: formData.aboutMe || '',
      street: formData.address?.street || '',
      city: formData.address?.city || '',
      state: formData.address?.state || '',
      zipCode: formData.address?.zipCode || '',
      birthdate: formData.birthdate || '',
    } as FormData,
  })

  // Redirect if not authenticated
  useEffect(() => {
    if (!token) {
      router.push('/')
    }
  }, [token, router])

  const onSubmit = async (data: FormData) => {
    if (!token) return

    setIsSubmitting(true)
    setError(null)

    try {
      // Update store
      const updates: Parameters<typeof updateFormData>[0] = {}

      if ('aboutMe' in data) {
        updates.aboutMe = data.aboutMe as string
      }
      if ('street' in data) {
        updates.address = {
          street: data.street as string,
          city: data.city as string,
          state: data.state as string,
          zipCode: data.zipCode as string,
        }
      }
      if ('birthdate' in data) {
        updates.birthdate = data.birthdate as string
      }

      updateFormData(updates)

      // Save to backend
      await api.updateProgress(token, {
        step: 3,
        about_me: 'aboutMe' in data ? (data.aboutMe as string) : undefined,
        street_address: 'street' in data ? (data.street as string) : undefined,
        city: 'city' in data ? (data.city as string) : undefined,
        state: 'state' in data ? (data.state as string) : undefined,
        zip_code: 'zipCode' in data ? (data.zipCode as string) : undefined,
        birthdate: 'birthdate' in data ? (data.birthdate as string) : undefined,
      })

      setStep(3)
      router.push('/step-3')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save progress')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleBack = () => {
    router.push('/')
  }

  const handleSkip = async () => {
    if (!token) return

    setIsSubmitting(true)
    setError(null)

    try {
      // Mark onboarding as complete and skip to dashboard
      await api.completeOnboarding(token)
      completeOnboarding()
      router.push('/complete')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (configLoading) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const aboutMeValue = watch('aboutMe') as string | undefined
  const birthdateValue = watch('birthdate') as string | undefined

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tell us about yourself</CardTitle>
        <CardDescription>
          Help us personalize your SupportIQ experience
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {components.map((component) => {
              if (component === 'aboutMe') {
                return (
                  <AboutMeField
                    key="aboutMe"
                    register={register as any}
                    errors={errors}
                    value={aboutMeValue}
                  />
                )
              }
              if (component === 'address') {
                return (
                  <AddressFields
                    key="address"
                    register={register as any}
                    errors={errors}
                  />
                )
              }
              if (component === 'birthdate') {
                return (
                  <BirthdateField
                    key="birthdate"
                    value={birthdateValue}
                    onChange={(val) => setValue('birthdate' as any, val, { shouldValidate: true })}
                    error={errors.birthdate?.message as string}
                  />
                )
              }
              return null
            })}

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

        <CardFooter className="flex-col sm:flex-row gap-2">
          <div className="flex gap-2 w-full sm:w-auto">
            <Button type="button" variant="ghost" onClick={handleBack}>
              Back
            </Button>
            <Button type="button" variant="outline" onClick={handleSkip} disabled={isSubmitting}>
              Skip to Dashboard
            </Button>
          </div>
          <Button type="submit" isLoading={isSubmitting} disabled={!isValid} className="w-full sm:w-auto sm:ml-auto">
            {isSubmitting ? 'Saving...' : 'Continue'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
