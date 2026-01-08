'use client'

import { useEffect, useCallback } from 'react'
import confetti from 'canvas-confetti'

interface ConfettiProps {
  trigger?: boolean
}

export function Confetti({ trigger = true }: ConfettiProps) {
  const fireConfetti = useCallback(() => {
    const duration = 3000
    const animationEnd = Date.now() + duration
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 1000 }

    function randomInRange(min: number, max: number) {
      return Math.random() * (max - min) + min
    }

    const interval: ReturnType<typeof setInterval> = setInterval(function () {
      const timeLeft = animationEnd - Date.now()

      if (timeLeft <= 0) {
        return clearInterval(interval)
      }

      const particleCount = 50 * (timeLeft / duration)

      // Confetti from the left
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
        colors: ['#8b5cf6', '#a78bfa', '#22c55e', '#60a5fa', '#f472b6'],
      })

      // Confetti from the right
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
        colors: ['#8b5cf6', '#a78bfa', '#22c55e', '#60a5fa', '#f472b6'],
      })
    }, 250)

    // Initial burst from center
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#8b5cf6', '#a78bfa', '#22c55e', '#60a5fa', '#f472b6'],
    })
  }, [])

  useEffect(() => {
    if (trigger) {
      // Small delay for dramatic effect
      const timeout = setTimeout(fireConfetti, 300)
      return () => clearTimeout(timeout)
    }
  }, [trigger, fireConfetti])

  return null
}
