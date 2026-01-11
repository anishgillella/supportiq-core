import { z } from 'zod'

// Step 1: Registration
export const registrationSchema = z
  .object({
    email: z
      .string()
      .min(1, 'Email is required')
      .email('Please enter a valid email address'),
    companyName: z
      .string()
      .min(1, 'Company name is required')
      .max(100, 'Company name must be under 100 characters'),
    companyWebsite: z
      .string()
      .min(1, 'Company website is required')
      .url('Please enter a valid URL (e.g., https://example.com)')
      .refine(
        (url) => url.startsWith('http://') || url.startsWith('https://'),
        { message: 'URL must start with http:// or https://' }
      ),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  })

export type RegistrationFormData = z.infer<typeof registrationSchema>

// About Me component
export const aboutMeSchema = z.object({
  aboutMe: z
    .string()
    .min(10, 'Please tell us a bit more about yourself (at least 10 characters)')
    .max(500, 'Please keep it under 500 characters'),
})

export type AboutMeFormData = z.infer<typeof aboutMeSchema>

// Address component
export const addressSchema = z.object({
  street: z.string().min(1, 'Street address is required'),
  city: z.string().min(1, 'City is required'),
  state: z.string().min(1, 'State is required'),
  zipCode: z
    .string()
    .min(1, 'ZIP code is required')
    .regex(/^\d{5}(-\d{4})?$/, 'Please enter a valid ZIP code (e.g., 12345 or 12345-6789)'),
})

export type AddressFormData = z.infer<typeof addressSchema>

// Birthdate component
export const birthdateSchema = z.object({
  birthdate: z
    .string()
    .min(1, 'Birthdate is required')
    .refine(
      (val) => {
        const date = new Date(val)
        const today = new Date()
        const age = today.getFullYear() - date.getFullYear()
        const monthDiff = today.getMonth() - date.getMonth()
        const dayDiff = today.getDate() - date.getDate()

        // Adjust age if birthday hasn't occurred this year
        const actualAge =
          monthDiff < 0 || (monthDiff === 0 && dayDiff < 0) ? age - 1 : age

        return actualAge >= 13
      },
      { message: 'You must be at least 13 years old' }
    ),
})

export type BirthdateFormData = z.infer<typeof birthdateSchema>

// Combined schema for dynamic step validation
export const stepSchemas = {
  aboutMe: aboutMeSchema,
  address: addressSchema,
  birthdate: birthdateSchema,
} as const

export type ComponentType = keyof typeof stepSchemas
