'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Ticket,
  Clock,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Circle,
  ArrowUpCircle,
  ArrowDownCircle,
  Phone,
  Mail,
  User,
  Tag,
  FileText,
  CheckSquare,
} from 'lucide-react'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { useOnboardingStore } from '@/stores/onboarding-store'

interface TicketDetail {
  id: string
  call_id: string
  user_id: string
  title: string
  description: string
  category: string
  priority: string
  status: string
  customer_email: string | null
  customer_name: string | null
  sentiment_score: number | null
  resolution_status: string | null
  customer_satisfaction_predicted: number | null
  action_items: string[]
  key_topics: string[]
  created_at: string
  updated_at: string
  resolved_at: string | null
  supportiq_voice_calls: {
    id: string
    vapi_call_id: string
    started_at: string
    duration_seconds: number | null
    status: string
  } | null
}

function PriorityBadge({ priority }: { priority: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    critical: {
      bg: 'bg-red-500/20',
      text: 'text-red-400',
      icon: <AlertCircle className="w-4 h-4" />,
    },
    high: {
      bg: 'bg-orange-500/20',
      text: 'text-orange-400',
      icon: <ArrowUpCircle className="w-4 h-4" />,
    },
    medium: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      icon: <AlertTriangle className="w-4 h-4" />,
    },
    low: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      icon: <ArrowDownCircle className="w-4 h-4" />,
    },
  }

  const cfg = config[priority] || config.medium

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm capitalize ${cfg.bg} ${cfg.text}`}>
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
      icon: <Circle className="w-4 h-4" />,
    },
    in_progress: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      icon: <Clock className="w-4 h-4" />,
    },
    resolved: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      icon: <CheckCircle className="w-4 h-4" />,
    },
    closed: {
      bg: 'bg-gray-500/20',
      text: 'text-gray-400',
      icon: <CheckCircle className="w-4 h-4" />,
    },
  }

  const cfg = config[status] || config.open

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm capitalize ${cfg.bg} ${cfg.text}`}>
      {cfg.icon}
      {status.replace(/_/g, ' ')}
    </span>
  )
}

function getSentimentLabel(score: number | null): { label: string; color: string } {
  if (score === null) return { label: 'Unknown', color: 'text-text-muted' }
  if (score >= 0.3) return { label: 'Positive', color: 'text-green-400' }
  if (score <= -0.3) return { label: 'Negative', color: 'text-red-400' }
  return { label: 'Neutral', color: 'text-yellow-400' }
}

export default function TicketDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { token } = useOnboardingStore()
  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ticketId = params.id as string

  const loadTicket = async () => {
    if (!token || !ticketId) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await api.getTicketDetail(token, ticketId)
      setTicket(data)
    } catch (e) {
      console.error('Failed to load ticket:', e)
      setError('Failed to load ticket')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTicket()
  }, [token, ticketId])

  const handleStatusChange = async (newStatus: string) => {
    if (!token || !ticket || updating) return

    try {
      setUpdating(true)
      await api.updateTicket(token, ticket.id, { status: newStatus })
      setTicket({ ...ticket, status: newStatus })
    } catch (e) {
      console.error('Failed to update status:', e)
    } finally {
      setUpdating(false)
    }
  }

  const handlePriorityChange = async (newPriority: string) => {
    if (!token || !ticket || updating) return

    try {
      setUpdating(true)
      await api.updateTicket(token, ticket.id, { priority: newPriority })
      setTicket({ ...ticket, priority: newPriority })
    } catch (e) {
      console.error('Failed to update priority:', e)
    } finally {
      setUpdating(false)
    }
  }

  const sentiment = ticket ? getSentimentLabel(ticket.sentiment_score) : null

  return (
    <AuthenticatedLayout>
      <div className="min-h-screen bg-bg-primary p-6">
        <div className="max-w-4xl mx-auto">
          {/* Back Button */}
          <Link
            href="/tickets"
            className="inline-flex items-center gap-2 text-text-muted hover:text-text-primary mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Tickets
          </Link>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary" />
            </div>
          ) : error ? (
            <div className="text-center py-20">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <p className="text-red-400">{error}</p>
            </div>
          ) : !ticket ? (
            <div className="text-center py-20">
              <Ticket className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-muted">Ticket not found</p>
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Header */}
              <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                <div className="flex flex-wrap items-start gap-3 mb-4">
                  <PriorityBadge priority={ticket.priority} />
                  <StatusBadge status={ticket.status} />
                  <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm bg-bg-tertiary text-text-muted capitalize">
                    <Tag className="w-4 h-4" />
                    {ticket.category?.replace(/_/g, ' ')}
                  </span>
                </div>

                <h1 className="text-2xl font-bold text-text-primary mb-2">{ticket.title}</h1>

                <div className="flex flex-wrap gap-4 text-sm text-text-muted">
                  <span>Created: {new Date(ticket.created_at).toLocaleString()}</span>
                  {ticket.resolved_at && (
                    <span>Resolved: {new Date(ticket.resolved_at).toLocaleString()}</span>
                  )}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                <h2 className="text-lg font-semibold text-text-primary mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-text-muted mb-2">Update Status</label>
                    <select
                      value={ticket.status}
                      onChange={(e) => handleStatusChange(e.target.value)}
                      disabled={updating}
                      className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border-primary text-text-primary disabled:opacity-50"
                    >
                      <option value="open">Open</option>
                      <option value="in_progress">In Progress</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-text-muted mb-2">Update Priority</label>
                    <select
                      value={ticket.priority}
                      onChange={(e) => handlePriorityChange(e.target.value)}
                      disabled={updating}
                      className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border-primary text-text-primary disabled:opacity-50"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-accent-primary" />
                  <h2 className="text-lg font-semibold text-text-primary">Description</h2>
                </div>
                <p className="text-text-secondary whitespace-pre-wrap">
                  {ticket.description || 'No description available'}
                </p>
              </div>

              {/* Customer Info & Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Customer Info */}
                <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <User className="w-5 h-5 text-accent-primary" />
                    <h2 className="text-lg font-semibold text-text-primary">Customer Info</h2>
                  </div>
                  <div className="space-y-3">
                    {ticket.customer_name && (
                      <div className="flex items-center gap-2 text-text-secondary">
                        <User className="w-4 h-4 text-text-muted" />
                        {ticket.customer_name}
                      </div>
                    )}
                    {ticket.customer_email && (
                      <div className="flex items-center gap-2 text-text-secondary">
                        <Mail className="w-4 h-4 text-text-muted" />
                        {ticket.customer_email}
                      </div>
                    )}
                    {!ticket.customer_name && !ticket.customer_email && (
                      <p className="text-text-muted">No customer info available</p>
                    )}
                  </div>
                </div>

                {/* Metrics */}
                <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <AlertTriangle className="w-5 h-5 text-accent-primary" />
                    <h2 className="text-lg font-semibold text-text-primary">Metrics</h2>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Sentiment</span>
                      <span className={sentiment?.color}>{sentiment?.label}</span>
                    </div>
                    {ticket.sentiment_score !== null && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Score</span>
                        <span className="text-text-secondary">
                          {(ticket.sentiment_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                    {ticket.customer_satisfaction_predicted !== null && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Predicted CSAT</span>
                        <span className="text-text-secondary">
                          {ticket.customer_satisfaction_predicted}/5
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-text-muted">Resolution</span>
                      <span className="text-text-secondary capitalize">
                        {ticket.resolution_status?.replace(/_/g, ' ') || 'Unknown'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Items */}
              {ticket.action_items && ticket.action_items.length > 0 && (
                <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <CheckSquare className="w-5 h-5 text-accent-primary" />
                    <h2 className="text-lg font-semibold text-text-primary">Action Items</h2>
                  </div>
                  <ul className="space-y-2">
                    {ticket.action_items.map((item, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-text-secondary"
                      >
                        <Circle className="w-2 h-2 mt-2 text-accent-primary flex-shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Key Topics */}
              {ticket.key_topics && ticket.key_topics.length > 0 && (
                <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Tag className="w-5 h-5 text-accent-primary" />
                    <h2 className="text-lg font-semibold text-text-primary">Key Topics</h2>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {ticket.key_topics.map((topic, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 rounded-full bg-bg-tertiary text-text-secondary text-sm"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Associated Call */}
              {ticket.supportiq_voice_calls && (
                <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Phone className="w-5 h-5 text-accent-primary" />
                    <h2 className="text-lg font-semibold text-text-primary">Associated Call</h2>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <p className="text-text-secondary">
                        {new Date(ticket.supportiq_voice_calls.started_at).toLocaleString()}
                      </p>
                      <p className="text-sm text-text-muted">
                        Duration: {ticket.supportiq_voice_calls.duration_seconds
                          ? `${Math.floor(ticket.supportiq_voice_calls.duration_seconds / 60)}:${(ticket.supportiq_voice_calls.duration_seconds % 60).toString().padStart(2, '0')}`
                          : 'N/A'
                        }
                      </p>
                    </div>
                    <Link
                      href={`/dashboard/calls/${ticket.supportiq_voice_calls.id}`}
                      className="px-4 py-2 rounded-lg bg-accent-primary text-white hover:bg-accent-primary/90 transition-colors"
                    >
                      View Call Details
                    </Link>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </AuthenticatedLayout>
  )
}
