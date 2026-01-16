'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Database,
  MessageSquare,
  BarChart3,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
  Ticket,
  Phone,
} from 'lucide-react'
import { useState } from 'react'
import { useOnboardingStore } from '@/stores/onboarding-store'

const navItems = [
  {
    label: 'Knowledge Base',
    href: '/knowledge',
    icon: Database,
    description: 'Manage your AI knowledge',
  },
  {
    label: 'AI Chat',
    href: '/chat',
    icon: MessageSquare,
    description: 'Chat with your AI assistant',
  },
  {
    label: 'Analytics',
    href: '/dashboard',
    icon: BarChart3,
    description: 'View call analytics',
  },
  {
    label: 'Calls',
    href: '/dashboard/calls',
    icon: Phone,
    description: 'View all calls',
  },
  {
    label: 'Tickets',
    href: '/tickets',
    icon: Ticket,
    description: 'View support tickets',
  },
  {
    label: 'User Data',
    href: '/data',
    icon: Users,
    description: 'View user information',
  },
  {
    label: 'Admin',
    href: '/admin',
    icon: Settings,
    description: 'Configure onboarding',
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { reset } = useOnboardingStore()
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  const handleLogout = () => {
    reset()
    router.push('/')
  }

  const NavContent = () => (
    <>
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <Link href="/knowledge" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-primary flex items-center justify-center">
            <span className="text-white font-bold text-sm">S</span>
          </div>
          <span className="font-semibold text-lg text-text-primary">SupportIQ</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsMobileOpen(false)}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
                ${isActive
                  ? 'bg-accent-primary/10 text-accent-primary'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
                }
              `}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-border">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg w-full text-text-secondary hover:text-error hover:bg-error/10 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </>
  )

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-bg-elevated border border-border text-text-primary"
      >
        {isMobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setIsMobileOpen(false)}
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
        />
      )}

      {/* Mobile Sidebar */}
      <motion.aside
        initial={{ x: -280 }}
        animate={{ x: isMobileOpen ? 0 : -280 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="lg:hidden fixed left-0 top-0 bottom-0 w-[280px] bg-bg-primary border-r border-border z-50 flex flex-col"
      >
        <NavContent />
      </motion.aside>

      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex fixed left-0 top-0 bottom-0 w-[260px] bg-bg-primary border-r border-border flex-col">
        <NavContent />
      </aside>
    </>
  )
}
