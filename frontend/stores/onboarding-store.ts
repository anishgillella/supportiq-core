import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AddressData {
  street: string
  city: string
  state: string
  zipCode: string
}

export interface OnboardingFormData {
  email: string
  aboutMe: string
  address: AddressData | null
  birthdate: string | null
}

interface OnboardingState {
  // Auth state
  userId: string | null
  token: string | null

  // Progress state
  currentStep: number
  isCompleted: boolean

  // Form data
  formData: OnboardingFormData

  // Actions
  setAuth: (userId: string, token: string) => void
  setStep: (step: number) => void
  updateFormData: (data: Partial<OnboardingFormData>) => void
  completeOnboarding: () => void
  reset: () => void
}

const initialFormData: OnboardingFormData = {
  email: '',
  aboutMe: '',
  address: null,
  birthdate: null,
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      // Initial state
      userId: null,
      token: null,
      currentStep: 1,
      isCompleted: false,
      formData: initialFormData,

      // Actions
      setAuth: (userId, token) => set({ userId, token }),

      setStep: (step) => set({ currentStep: step }),

      updateFormData: (data) =>
        set((state) => ({
          formData: { ...state.formData, ...data },
        })),

      completeOnboarding: () => set({ isCompleted: true }),

      reset: () =>
        set({
          userId: null,
          token: null,
          currentStep: 1,
          isCompleted: false,
          formData: initialFormData,
        }),
    }),
    {
      name: 'supportiq-onboarding',
      // Only persist certain fields
      partialize: (state) => ({
        userId: state.userId,
        token: state.token,
        currentStep: state.currentStep,
        isCompleted: state.isCompleted,
        formData: state.formData,
      }),
    }
  )
)
