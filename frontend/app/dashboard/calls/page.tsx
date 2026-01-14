'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Phone,
  Clock,
  ChevronLeft,
  ChevronRight,
  Smile,
  Meh,
  Frown,
  AlertTriangle,
  Filter,
} from 'lucide-react'
import { api } from '@/lib/api'

interface Call {
  id: string
  vapi_call_id: string
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  status: string
  agent_type: string
  sentiment: string | null
  category: string | null
  resolution: string | null
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return 'N/A'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function SentimentBadge({ sentiment }: { sentiment?: string | null }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode; label: string }> = {
    positive: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      icon: <Smile className="w-3 h-3" />,
      label: 'Positive',
    },
    neutral: {
      bg: 'bg-gray-500/20',
      text: 'text-gray-400',
      icon: <Meh className="w-3 h-3" />,
      label: 'Neutral',
    },
    negative: {
      bg: 'bg-red-500/20',
      text: 'text-red-400',
      icon: <Frown className="w-3 h-3" />,
      label: 'Negative',
    },
    mixed: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      icon: <AlertTriangle className="w-3 h-3" />,
      label: 'Mixed',
    },
  }

  const cfg = config[sentiment || 'neutral'] || config.neutral

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${cfg.bg} ${cfg.text}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    completed: { bg: 'bg-green-500/20', text: 'text-green-400' },
    in_progress: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    abandoned: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
    failed: { bg: 'bg-red-500/20', text: 'text-red-400' },
  }

  const cfg = config[status] || config.completed

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs capitalize ${cfg.bg} ${cfg.text}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export default function CallsListPage() {
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sentimentFilter, setSentimentFilter] = useState<string>('')
  const pageSize = 20

  const loadCalls = async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await api.getVoiceCalls({
        page,
        pageSize,
        status: statusFilter || undefined,
        sentiment: sentimentFilter || undefined,
      })
      setCalls(result.calls)
      setTotal(result.total)
    } catch (e) {
      setError('Failed to load calls')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCalls()
  }, [page, statusFilter, sentimentFilter])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="min-h-screen bg-bg-primary p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/dashboard"
            className="p-2 rounded-lg hover:bg-bg-secondary transition-colors text-text-muted hover:text-text-primary"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <Phone className="w-6 h-6 text-accent-primary" />
              All Calls
            </h1>
            <p className="text-text-muted">{total} total calls</p>
          </div>
        </div>

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
              <option value="completed">Completed</option>
              <option value="in_progress">In Progress</option>
              <option value="abandoned">Abandoned</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <select
            value={sentimentFilter}
            onChange={(e) => {
              setSentimentFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border-primary text-text-primary text-sm"
          >
            <option value="">All Sentiments</option>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
            <option value="mixed">Mixed</option>
          </select>
        </div>

        {/* Calls Table */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-text-muted">{error}</p>
            <button
              onClick={loadCalls}
              className="mt-4 px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/90"
            >
              Retry
            </button>
          </div>
        ) : calls.length === 0 ? (
          <div className="text-center py-20">
            <Phone className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted">No calls found</p>
          </div>
        ) : (
          <>
            <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
              <table className="w-full">
                <thead className="bg-bg-tertiary">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-text-muted">Date & Time</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-text-muted">Duration</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-text-muted">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-text-muted">Category</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-text-muted">Sentiment</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-text-muted">Resolution</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-primary">
                  {calls.map((call, i) => (
                    <motion.tr
                      key={call.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="hover:bg-bg-tertiary/50 transition-colors cursor-pointer"
                      onClick={() => (window.location.href = `/dashboard/calls/${call.id}`)}
                    >
                      <td className="px-4 py-3">
                        <div className="text-sm text-text-primary">
                          {new Date(call.started_at).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-text-muted">
                          {new Date(call.started_at).toLocaleTimeString()}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-sm text-text-muted">
                          <Clock className="w-3 h-3" />
                          {formatDuration(call.duration_seconds)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={call.status} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-text-muted capitalize">
                          {call.category?.replace(/_/g, ' ') || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {call.sentiment ? <SentimentBadge sentiment={call.sentiment} /> : <span className="text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-text-muted capitalize">
                          {call.resolution?.replace(/_/g, ' ') || '—'}
                        </span>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
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
  )
}
