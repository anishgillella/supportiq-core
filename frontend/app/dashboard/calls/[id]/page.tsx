'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Clock,
  User,
  Bot,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Lightbulb,
  Play,
  Smile,
  Meh,
  Frown,
  Tag,
  MessageSquare,
} from 'lucide-react'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { useOnboardingStore } from '@/stores/onboarding-store'

interface CallDetail {
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
  transcript: Array<{
    role: string
    content: string
    timestamp?: number
  }> | null
  analytics: {
    overall_sentiment: string
    sentiment_score: number
    sentiment_progression: Array<{ timestamp: number; sentiment: string }>
    primary_category: string
    secondary_categories: string[]
    resolution_status: string
    customer_satisfaction_predicted: number
    agent_performance_score: number
    customer_intent: string
    key_topics: string[]
    action_items: string[]
    improvement_suggestions: string[]
    call_summary: string
  } | null
  recording_url: string | null
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
      icon: <AlertTriangle className="w-4 h-4" />,
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

function formatDuration(seconds: number | null): string {
  if (!seconds) return 'N/A'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export default function CallDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { token } = useOnboardingStore()
  const callId = params.id as string

  const [call, setCall] = useState<CallDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadCall = async () => {
      if (!token) {
        setLoading(false)
        return
      }
      try {
        setLoading(true)
        const result = await api.getCallDetail(token, callId)
        setCall(result)
      } catch (e) {
        setError('Failed to load call details')
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    loadCall()
  }, [callId, token])

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="min-h-screen bg-bg-primary flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent-primary" />
        </div>
      </AuthenticatedLayout>
    )
  }

  if (error || !call) {
    return (
      <AuthenticatedLayout>
        <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center">
          <p className="text-text-muted">{error || 'Call not found'}</p>
          <Link href="/dashboard" className="mt-4 text-accent-primary hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </AuthenticatedLayout>
    )
  }

  const analytics = call.analytics

  return (
    <AuthenticatedLayout>
    <div className="min-h-screen bg-bg-primary p-6">
      <div className="max-w-5xl mx-auto">
        {/* Back Button */}
        <Link
          href="/dashboard"
          className="inline-flex items-center text-text-muted hover:text-text-primary mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-bg-secondary rounded-xl border border-border-primary p-6 mb-6"
        >
          <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
            <div>
              <h1 className="text-2xl font-bold text-text-primary">Call Details</h1>
              <p className="text-text-muted">{new Date(call.started_at).toLocaleString()}</p>
            </div>
            <SentimentBadge sentiment={analytics?.overall_sentiment} size="lg" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div>
              <p className="text-sm text-text-muted">Duration</p>
              <p className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <Clock className="w-4 h-4 text-text-muted" />
                {formatDuration(call.duration_seconds)}
              </p>
            </div>
            <div>
              <p className="text-sm text-text-muted">Category</p>
              <p className="text-lg font-semibold text-text-primary capitalize flex items-center gap-2">
                <Tag className="w-4 h-4 text-text-muted" />
                {analytics?.primary_category?.replace(/_/g, ' ') || 'Unknown'}
              </p>
            </div>
            <div>
              <p className="text-sm text-text-muted">Resolution</p>
              <p className="text-lg font-semibold text-text-primary capitalize flex items-center gap-2">
                {analytics?.resolution_status === 'resolved' ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : analytics?.resolution_status === 'escalated' ? (
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
                {analytics?.resolution_status?.replace(/_/g, ' ') || 'Unknown'}
              </p>
            </div>
            <div>
              <p className="text-sm text-text-muted">CSAT Predicted</p>
              <p className="text-lg font-semibold text-text-primary">
                {analytics?.customer_satisfaction_predicted?.toFixed(1) || 'N/A'} / 5.0
              </p>
            </div>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Transcript */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2 bg-bg-secondary rounded-xl border border-border-primary p-6"
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Transcript
              </h2>
              {call.recording_url && (
                <button className="flex items-center text-accent-primary hover:text-accent-primary/80 text-sm">
                  <Play className="w-4 h-4 mr-1" />
                  Play Recording
                </button>
              )}
            </div>

            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
              {call.transcript && call.transcript.length > 0 ? (
                call.transcript.map((message, i) => {
                  const isAgent = message.role === 'assistant' || message.role === 'bot' || message.role === 'ai'
                  return (
                    <div key={i} className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
                      <div className={`max-w-[80%] p-3 rounded-lg ${isAgent ? 'bg-accent-primary/10' : 'bg-bg-tertiary'}`}>
                        <div className="flex items-center gap-2 mb-1">
                          {isAgent ? (
                            <Bot className="w-4 h-4 text-accent-primary" />
                          ) : (
                            <User className="w-4 h-4 text-text-muted" />
                          )}
                          <span className="text-xs font-medium text-text-muted uppercase">
                            {isAgent ? 'Agent' : 'Customer'}
                          </span>
                          {message.timestamp !== undefined && (
                            <span className="text-xs text-text-muted">{message.timestamp}s</span>
                          )}
                        </div>
                        <p className="text-sm text-text-primary">{message.content}</p>
                      </div>
                    </div>
                  )
                })
              ) : (
                <p className="text-text-muted text-center py-8">No transcript available</p>
              )}
            </div>
          </motion.div>

          {/* Analysis Panel */}
          <div className="space-y-6">
            {/* Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-3">Summary</h2>
              <p className="text-text-muted text-sm">{analytics?.call_summary || 'No summary available'}</p>
            </motion.div>

            {/* Customer Intent */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-3">Customer Intent</h2>
              <p className="text-text-muted text-sm">{analytics?.customer_intent || 'Not identified'}</p>
            </motion.div>

            {/* Key Topics */}
            {analytics?.key_topics && analytics.key_topics.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-6"
              >
                <h2 className="text-lg font-semibold text-text-primary mb-3">Key Topics</h2>
                <div className="flex flex-wrap gap-2">
                  {analytics.key_topics.map((topic, i) => (
                    <span key={i} className="px-2 py-1 bg-bg-tertiary text-text-muted rounded-full text-sm">
                      {topic}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Improvement Suggestions */}
            {analytics?.improvement_suggestions && analytics.improvement_suggestions.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="bg-yellow-500/10 rounded-xl border border-yellow-500/30 p-6"
              >
                <h2 className="text-lg font-semibold text-yellow-400 mb-3 flex items-center gap-2">
                  <Lightbulb className="w-5 h-5" />
                  Improvement Suggestions
                </h2>
                <ul className="space-y-2">
                  {analytics.improvement_suggestions.map((suggestion, i) => (
                    <li key={i} className="text-sm text-yellow-300/80 flex items-start">
                      <span className="mr-2">•</span>
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Action Items */}
            {analytics?.action_items && analytics.action_items.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-accent-primary/10 rounded-xl border border-accent-primary/30 p-6"
              >
                <h2 className="text-lg font-semibold text-accent-primary mb-3">Action Items</h2>
                <ul className="space-y-2">
                  {analytics.action_items.map((item, i) => (
                    <li key={i} className="text-sm text-text-muted flex items-start">
                      <CheckCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0 text-accent-primary" />
                      {item}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Agent Performance */}
            {analytics?.agent_performance_score !== undefined && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-6"
              >
                <h2 className="text-lg font-semibold text-text-primary mb-3">Agent Performance</h2>
                <div className="flex items-center">
                  <div className="flex-1 h-3 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        analytics.agent_performance_score >= 80
                          ? 'bg-green-500'
                          : analytics.agent_performance_score >= 60
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${analytics.agent_performance_score}%` }}
                    />
                  </div>
                  <span className="ml-3 font-semibold text-text-primary">
                    {analytics.agent_performance_score.toFixed(0)}/100
                  </span>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
    </AuthenticatedLayout>
  )
}
