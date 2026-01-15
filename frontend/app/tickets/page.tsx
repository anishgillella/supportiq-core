'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Ticket,
  Clock,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Circle,
  Filter,
  ArrowUpCircle,
  ArrowDownCircle,
} from 'lucide-react'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { useOnboardingStore } from '@/stores/onboarding-store'

interface TicketData {
  id: string
  call_id: string
  title: string
  description: string
  category: string
  priority: string
  status: string
  customer_email: string | null
  sentiment_score: number | null
  action_items: string[]
  created_at: string
  updated_at: string
}

interface TicketStats {
  total: number
  by_status: {
    open: number
    in_progress: number
    resolved: number
  }
  by_priority: {
    critical: number
    high: number
    medium: number
    low: number
  }
}

function PriorityBadge({ priority }: { priority: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    critical: {
      bg: 'bg-red-500/20',
      text: 'text-red-400',
      icon: <AlertCircle className="w-3 h-3" />,
    },
    high: {
      bg: 'bg-orange-500/20',
      text: 'text-orange-400',
      icon: <ArrowUpCircle className="w-3 h-3" />,
    },
    medium: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
    low: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      icon: <ArrowDownCircle className="w-3 h-3" />,
    },
  }

  const cfg = config[priority] || config.medium

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs capitalize ${cfg.bg} ${cfg.text}`}>
      {cfg.icon}
      {priority}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    open: {
      bg: 'bg-blue-500/20',
      text: 'text-blue-400',
      icon: <Circle className="w-3 h-3" />,
    },
    in_progress: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      icon: <Clock className="w-3 h-3" />,
    },
    resolved: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      icon: <CheckCircle className="w-3 h-3" />,
    },
    closed: {
      bg: 'bg-gray-500/20',
      text: 'text-gray-400',
      icon: <CheckCircle className="w-3 h-3" />,
    },
  }

  const cfg = config[status] || config.open

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs capitalize ${cfg.bg} ${cfg.text}`}>
      {cfg.icon}
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export default function TicketsPage() {
  const router = useRouter()
  const { token } = useOnboardingStore()
  const [tickets, setTickets] = useState<TicketData[]>([])
  const [stats, setStats] = useState<TicketStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [priorityFilter, setPriorityFilter] = useState<string>('')
  const pageSize = 20

  const loadData = async () => {
    if (!token) {
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      const [ticketsResult, statsResult] = await Promise.all([
        api.getTickets(token, {
          page,
          pageSize,
          status: statusFilter || undefined,
          priority: priorityFilter || undefined,
        }),
        api.getTicketStats(token),
      ])
      setTickets(ticketsResult.tickets)
      setTotal(ticketsResult.total)
      setStats(statsResult)
    } catch (e) {
      console.error('Failed to load tickets:', e)
      setTickets([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [page, statusFilter, priorityFilter, token])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <AuthenticatedLayout>
      <div className="min-h-screen bg-bg-primary p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
                <Ticket className="w-6 h-6 text-accent-primary" />
                Support Tickets
              </h1>
              <p className="text-text-muted">{total} total tickets</p>
            </div>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <div className="flex items-center gap-2 text-blue-400 mb-2">
                  <Circle className="w-4 h-4" />
                  <span className="text-sm font-medium">Open</span>
                </div>
                <p className="text-2xl font-bold text-text-primary">{stats.by_status.open}</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <div className="flex items-center gap-2 text-yellow-400 mb-2">
                  <Clock className="w-4 h-4" />
                  <span className="text-sm font-medium">In Progress</span>
                </div>
                <p className="text-2xl font-bold text-text-primary">{stats.by_status.in_progress}</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <div className="flex items-center gap-2 text-green-400 mb-2">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Resolved</span>
                </div>
                <p className="text-2xl font-bold text-text-primary">{stats.by_status.resolved}</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <div className="flex items-center gap-2 text-red-400 mb-2">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Critical</span>
                </div>
                <p className="text-2xl font-bold text-text-primary">{stats.by_priority.critical}</p>
              </motion.div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-6">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-muted" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
                className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border-primary text-text-primary text-sm"
              >
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <select
              value={priorityFilter}
              onChange={(e) => {
                setPriorityFilter(e.target.value)
                setPage(1)
              }}
              className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border-primary text-text-primary text-sm"
            >
              <option value="">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Tickets List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary" />
            </div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-20">
              <Ticket className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-muted">No tickets found</p>
              <p className="text-text-muted text-sm mt-2">Tickets are automatically created after each call</p>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {tickets.map((ticket, i) => (
                  <motion.div
                    key={ticket.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.02 }}
                    onClick={() => router.push(`/tickets/${ticket.id}`)}
                    className="bg-bg-secondary rounded-xl border border-border-primary p-4 hover:border-accent-primary/50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <PriorityBadge priority={ticket.priority} />
                          <StatusBadge status={ticket.status} />
                          <span className="text-xs text-text-muted capitalize">
                            {ticket.category?.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <h3 className="text-text-primary font-medium truncate">{ticket.title}</h3>
                        <p className="text-text-muted text-sm mt-1 line-clamp-2">{ticket.description}</p>
                        {ticket.action_items && ticket.action_items.length > 0 && (
                          <p className="text-xs text-accent-primary mt-2">
                            {ticket.action_items.length} action item{ticket.action_items.length > 1 ? 's' : ''}
                          </p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-xs text-text-muted">
                          {new Date(ticket.created_at).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-text-muted">
                          {new Date(ticket.created_at).toLocaleTimeString()}
                        </p>
                        {ticket.customer_email && (
                          <p className="text-xs text-text-muted mt-2 truncate max-w-[150px]">
                            {ticket.customer_email}
                          </p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-6">
                  <p className="text-sm text-text-muted">
                    Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 rounded-lg bg-bg-secondary border border-border-primary text-text-muted hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-text-muted">
                      Page {page} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="p-2 rounded-lg bg-bg-secondary border border-border-primary text-text-muted hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AuthenticatedLayout>
  )
}
