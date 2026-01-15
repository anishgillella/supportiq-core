'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Database, RefreshCw, User, Mail, Calendar, MapPin, FileText, Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import { PublicLayout } from '@/components/layout/public-layout'

interface UserData {
  id: string
  email: string
  current_step: number
  onboarding_completed: boolean
  created_at: string
  profile: {
    about_me: string | null
    street_address: string | null
    city: string | null
    state: string | null
    zip_code: string | null
    birthdate: string | null
  } | null
}

export default function DataPage() {
  const [users, setUsers] = useState<UserData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchUsers = async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true)
    setError(null)

    try {
      const data = await api.getAllUsers()
      setUsers(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users')
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchUsers()

    // Auto-refresh every 10 seconds
    const interval = setInterval(() => fetchUsers(), 10000)
    return () => clearInterval(interval)
  }, [])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <PublicLayout>
        <div className="min-h-screen bg-bg-primary flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
        </div>
      </PublicLayout>
    )
  }

  return (
    <PublicLayout>
    <div className="min-h-screen bg-bg-primary py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-accent-primary flex items-center justify-center">
                <Database className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-text-primary">User Data</h1>
            </div>
            <p className="text-text-secondary">
              View all registered users and their onboarding progress
            </p>
          </div>
          <Button
            variant="secondary"
            onClick={() => fetchUsers(true)}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={cn('w-4 h-4 mr-2', isRefreshing && 'animate-spin')}
            />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-xl bg-error/10 border border-error/20 text-error"
          >
            {error}
          </motion.div>
        )}

        {users.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-16"
          >
            <div className="w-16 h-16 rounded-full bg-bg-secondary flex items-center justify-center mx-auto mb-4">
              <User className="w-8 h-8 text-text-muted" />
            </div>
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              No users yet
            </h2>
            <p className="text-text-secondary mb-4">
              Users will appear here after they register
            </p>
            <Button onClick={() => (window.location.href = '/')}>
              Go to Onboarding
            </Button>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="overflow-x-auto"
          >
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      Email
                    </div>
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      About Me
                    </div>
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      Address
                    </div>
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Birthdate
                    </div>
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    Step
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    Completed
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-medium text-text-muted">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user, index) => (
                  <motion.tr
                    key={user.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="border-b border-border hover:bg-bg-secondary/50 transition-colors"
                  >
                    <td className="py-4 px-4">
                      <span className="text-text-primary font-medium">
                        {user.email}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      {user.profile?.about_me ? (
                        <span
                          className="text-text-secondary text-sm max-w-[200px] truncate block"
                          title={user.profile.about_me}
                        >
                          {user.profile.about_me}
                        </span>
                      ) : (
                        <span className="text-text-muted text-sm">—</span>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      {user.profile?.street_address ? (
                        <div className="text-sm">
                          <span className="text-text-secondary block">
                            {user.profile.street_address}
                          </span>
                          <span className="text-text-muted">
                            {user.profile.city}, {user.profile.state}{' '}
                            {user.profile.zip_code}
                          </span>
                        </div>
                      ) : (
                        <span className="text-text-muted text-sm">—</span>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      {user.profile?.birthdate ? (
                        <span className="text-text-secondary text-sm">
                          {formatDate(user.profile.birthdate)}
                        </span>
                      ) : (
                        <span className="text-text-muted text-sm">—</span>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                          user.current_step === 1 && 'bg-blue-500/20 text-blue-400',
                          user.current_step === 2 && 'bg-yellow-500/20 text-yellow-400',
                          user.current_step === 3 && 'bg-purple-500/20 text-purple-400',
                          user.current_step >= 4 && 'bg-green-500/20 text-green-400'
                        )}
                      >
                        Step {Math.min(user.current_step, 3)}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      {user.onboarding_completed ? (
                        <div className="flex items-center gap-1 text-success">
                          <Check className="w-4 h-4" />
                          <span className="text-sm">Yes</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-text-muted">
                          <X className="w-4 h-4" />
                          <span className="text-sm">No</span>
                        </div>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <span className="text-text-muted text-sm">
                        {formatDateTime(user.created_at)}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        )}

        {/* Summary stats */}
        {users.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4"
          >
            <div className="p-4 rounded-xl bg-bg-secondary border border-border">
              <div className="text-2xl font-bold text-text-primary">
                {users.length}
              </div>
              <div className="text-sm text-text-muted">Total Users</div>
            </div>
            <div className="p-4 rounded-xl bg-bg-secondary border border-border">
              <div className="text-2xl font-bold text-success">
                {users.filter((u) => u.onboarding_completed).length}
              </div>
              <div className="text-sm text-text-muted">Completed</div>
            </div>
            <div className="p-4 rounded-xl bg-bg-secondary border border-border">
              <div className="text-2xl font-bold text-yellow-400">
                {users.filter((u) => !u.onboarding_completed).length}
              </div>
              <div className="text-sm text-text-muted">In Progress</div>
            </div>
            <div className="p-4 rounded-xl bg-bg-secondary border border-border">
              <div className="text-2xl font-bold text-accent-primary">
                {users.length > 0
                  ? Math.round(
                      (users.filter((u) => u.onboarding_completed).length /
                        users.length) *
                        100
                    )
                  : 0}
                %
              </div>
              <div className="text-sm text-text-muted">Completion Rate</div>
            </div>
          </motion.div>
        )}

        {/* Navigation links */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 flex flex-wrap justify-center gap-4 text-sm"
        >
          <a href="/knowledge" className="text-accent-primary hover:underline">
            Knowledge Base →
          </a>
          <a href="/chat" className="text-accent-primary hover:underline">
            AI Chat →
          </a>
          <a href="/" className="text-accent-primary hover:underline">
            View Onboarding →
          </a>
          <a href="/admin" className="text-accent-primary hover:underline">
            Admin Panel →
          </a>
        </motion.div>
      </div>
    </div>
    </PublicLayout>
  )
}
