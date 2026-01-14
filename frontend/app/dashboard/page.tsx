'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Phone,
  Clock,
  CheckCircle,
  TrendingUp,
  AlertCircle,
  Smile,
  Meh,
  Frown,
  ArrowLeft,
  BarChart3,
  MessageSquare,
  RefreshCw,
} from 'lucide-react'
import { api } from '@/lib/api'

interface DashboardData {
  overview: {
    total_calls: number
    avg_duration_seconds: number
    resolution_rate: number
    avg_sentiment_score: number
    calls_today: number
    calls_this_week: number
  }
  sentiment: {
    positive: number
    neutral: number
    negative: number
    mixed: number
  }
  categories: {
    categories: Record<string, number>
  }
  trends: Array<{
    date: string
    calls: number
    avg_sentiment: number
    resolution_rate: number
  }>
  top_issues: Array<{ category: string; count: number }>
  recent_calls: Array<{
    id: string
    started_at: string
    duration: number | null
    status: string
    sentiment: string | null
  }>
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function SentimentBadge({ sentiment, size = 'md' }: { sentiment?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  }

  const config: Record<string, { bg: string; text: string; icon: React.ReactNode; label: string }> = {
    positive: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      icon: <Smile className="w-4 h-4" />,
      label: 'Positive',
    },
    neutral: {
      bg: 'bg-gray-500/20',
      text: 'text-gray-400',
      icon: <Meh className="w-4 h-4" />,
      label: 'Neutral',
    },
    negative: {
      bg: 'bg-red-500/20',
      text: 'text-red-400',
      icon: <Frown className="w-4 h-4" />,
      label: 'Negative',
    },
    mixed: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      icon: <AlertCircle className="w-4 h-4" />,
      label: 'Mixed',
    },
  }

  const cfg = config[sentiment || 'neutral'] || config.neutral

  return (
    <span className={`inline-flex items-center gap-1 rounded-full ${cfg.bg} ${cfg.text} ${sizeClasses[size]}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

function StatsCard({
  title,
  value,
  icon,
  subtitle,
  color = 'blue',
}: {
  title: string
  value: string | number
  icon: React.ReactNode
  subtitle?: string
  color?: 'blue' | 'green' | 'purple' | 'red' | 'gray'
}) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
    purple: 'bg-purple-500/20 text-purple-400',
    red: 'bg-red-500/20 text-red-400',
    gray: 'bg-gray-500/20 text-gray-400',
  }

  return (
    <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-text-muted">{title}</p>
          <p className="text-2xl font-bold text-text-primary mt-1">{value}</p>
          {subtitle && <p className="text-xs text-text-muted mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState(7)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await api.getAnalyticsDashboard(dateRange)
      setData(result)
    } catch (e) {
      setError('Failed to load dashboard data')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [dateRange])

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-text-muted">{error}</p>
        <button
          onClick={loadData}
          className="mt-4 px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/90"
        >
          Retry
        </button>
      </div>
    )
  }

  const overview = data?.overview || {
    total_calls: 0,
    avg_duration_seconds: 0,
    resolution_rate: 0,
    avg_sentiment_score: 0,
    calls_today: 0,
    calls_this_week: 0,
  }

  const sentiment = data?.sentiment || { positive: 0, neutral: 0, negative: 0, mixed: 0 }
  const categories = data?.categories?.categories || {}
  const trends = data?.trends || []
  const topIssues = data?.top_issues || []
  const recentCalls = data?.recent_calls || []

  const totalSentiment = sentiment.positive + sentiment.neutral + sentiment.negative + sentiment.mixed

  return (
    <div className="min-h-screen bg-bg-primary p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div className="flex items-center gap-4">
            <Link
              href="/chat"
              className="p-2 rounded-lg hover:bg-bg-secondary transition-colors text-text-muted hover:text-text-primary"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-text-primary flex items-center gap-3">
                <BarChart3 className="w-8 h-8 text-accent-primary" />
                Voice Analytics
              </h1>
              <p className="text-text-muted">Customer call insights and performance metrics</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2 rounded-lg hover:bg-bg-secondary transition-colors text-text-muted hover:text-text-primary"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(Number(e.target.value))}
              className="px-4 py-2 rounded-lg bg-bg-secondary border border-border-primary text-text-primary"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Total Calls"
            value={overview.total_calls}
            icon={<Phone className="w-6 h-6" />}
            subtitle={`${overview.calls_today} today`}
            color="blue"
          />
          <StatsCard
            title="Avg Duration"
            value={formatDuration(overview.avg_duration_seconds)}
            icon={<Clock className="w-6 h-6" />}
            color="purple"
          />
          <StatsCard
            title="Resolution Rate"
            value={`${overview.resolution_rate.toFixed(1)}%`}
            icon={<CheckCircle className="w-6 h-6" />}
            color="green"
          />
          <StatsCard
            title="Avg Sentiment"
            value={overview.avg_sentiment_score > 0.3 ? 'Positive' : overview.avg_sentiment_score < -0.3 ? 'Negative' : 'Neutral'}
            icon={<TrendingUp className="w-6 h-6" />}
            color={overview.avg_sentiment_score > 0 ? 'green' : overview.avg_sentiment_score < 0 ? 'red' : 'gray'}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sentiment Breakdown */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-bg-secondary rounded-xl border border-border-primary p-6"
          >
            <h2 className="text-lg font-semibold text-text-primary mb-4">Sentiment Breakdown</h2>
            <div className="space-y-4">
              {[
                { icon: <Smile className="w-5 h-5 text-green-400" />, label: 'Positive', count: sentiment.positive, color: 'green' },
                { icon: <Meh className="w-5 h-5 text-gray-400" />, label: 'Neutral', count: sentiment.neutral, color: 'gray' },
                { icon: <Frown className="w-5 h-5 text-red-400" />, label: 'Negative', count: sentiment.negative, color: 'red' },
              ].map((item) => {
                const percentage = totalSentiment > 0 ? (item.count / totalSentiment) * 100 : 0
                return (
                  <div key={item.label} className="flex items-center gap-3">
                    {item.icon}
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-text-muted">{item.label}</span>
                        <span className="text-text-primary font-medium">{item.count}</span>
                      </div>
                      <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full bg-${item.color}-500`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* Top Issues */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-bg-secondary rounded-xl border border-border-primary p-6"
          >
            <h2 className="text-lg font-semibold text-text-primary mb-4">Top Issue Categories</h2>
            <div className="space-y-3">
              {topIssues.length > 0 ? (
                topIssues.map((issue, i) => (
                  <div key={i} className="flex justify-between items-center">
                    <span className="text-text-muted capitalize">{issue.category.replace(/_/g, ' ')}</span>
                    <span className="px-2 py-1 bg-accent-primary/20 text-accent-primary rounded-full text-sm">
                      {issue.count}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-text-muted text-sm">No data yet</p>
              )}
            </div>
          </motion.div>

          {/* Recent Calls */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-bg-secondary rounded-xl border border-border-primary p-6"
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-text-primary">Recent Calls</h2>
              <Link href="/dashboard/calls" className="text-accent-primary text-sm hover:underline">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              {recentCalls.length > 0 ? (
                recentCalls.map((call) => (
                  <Link
                    key={call.id}
                    href={`/dashboard/calls/${call.id}`}
                    className="block p-3 rounded-lg hover:bg-bg-tertiary transition-colors"
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="text-sm text-text-muted">
                          {new Date(call.started_at).toLocaleString()}
                        </p>
                        <p className="text-xs text-text-muted">
                          {call.duration ? formatDuration(call.duration) : 'N/A'}
                        </p>
                      </div>
                      <SentimentBadge sentiment={call.sentiment} size="sm" />
                    </div>
                  </Link>
                ))
              ) : (
                <p className="text-text-muted text-sm">No calls yet</p>
              )}
            </div>
          </motion.div>
        </div>

        {/* Trends Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8 bg-bg-secondary rounded-xl border border-border-primary p-6"
        >
          <h2 className="text-lg font-semibold text-text-primary mb-4">Call Volume Trend</h2>
          {trends.length > 0 ? (
            <div className="h-64 flex items-end justify-between gap-2">
              {trends.map((day, i) => {
                const maxCalls = Math.max(...trends.map((t) => t.calls), 1)
                const height = Math.max(10, (day.calls / maxCalls) * 200)
                return (
                  <div key={i} className="flex-1 flex flex-col items-center">
                    <div
                      className="w-full bg-accent-primary rounded-t transition-all hover:bg-accent-primary/80"
                      style={{ height: `${height}px` }}
                      title={`${day.calls} calls`}
                    />
                    <span className="text-xs text-text-muted mt-2">
                      {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}
                    </span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-text-muted">
              No trend data available
            </div>
          )}
        </motion.div>

        {/* Quick Actions */}
        <div className="mt-8 flex flex-wrap gap-4">
          <Link
            href="/chat"
            className="flex items-center gap-2 px-4 py-2 bg-bg-secondary border border-border-primary rounded-lg text-text-secondary hover:bg-bg-tertiary transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            Text Chat
          </Link>
          <Link
            href="/dashboard/calls"
            className="flex items-center gap-2 px-4 py-2 bg-bg-secondary border border-border-primary rounded-lg text-text-secondary hover:bg-bg-tertiary transition-colors"
          >
            <Phone className="w-4 h-4" />
            All Calls
          </Link>
        </div>
      </div>
    </div>
  )
}
