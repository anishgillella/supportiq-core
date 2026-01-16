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
  TrendingUp,
  MessagesSquare,
} from 'lucide-react'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { useOnboardingStore } from '@/stores/onboarding-store'

interface SentimentProgressionItem {
  timestamp: number
  sentiment: string
  trigger?: string
}

interface HandleTimeBreakdown {
  talk_time_seconds?: number
  hold_time_seconds?: number
  silence_time_seconds?: number
  agent_talk_percentage?: number
  customer_talk_percentage?: number
}

interface ConversationQuality {
  clarity_score?: number
  empathy_phrases_count?: number
  jargon_usage_count?: number
  avg_agent_response_time_seconds?: number
}

interface CompetitiveIntelligence {
  competitors_mentioned?: string[]
  switching_intent_detected?: boolean
  price_sensitivity_level?: string
}

interface ProductAnalytics {
  products_discussed?: string[]
  features_requested?: string[]
  features_problematic?: string[]
  upsell_opportunity_detected?: boolean
}

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
    sentiment_progression: SentimentProgressionItem[]
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
    // New granular analytics
    customer_effort_score?: number
    customer_had_to_repeat?: boolean
    transfer_count?: number
    was_escalated?: boolean
    escalation_reason?: string
    handle_time_breakdown?: HandleTimeBreakdown
    conversation_quality?: ConversationQuality
    competitive_intelligence?: CompetitiveIntelligence
    product_analytics?: ProductAnalytics
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

// Sentiment Timeline Component
function SentimentTimeline({
  progression,
  totalDuration
}: {
  progression: SentimentProgressionItem[]
  totalDuration: number | null
}) {
  if (!progression || progression.length === 0) return null

  const sentimentColors: Record<string, { bg: string; border: string; label: string }> = {
    positive: { bg: 'bg-green-500', border: 'border-green-400', label: 'Positive' },
    neutral: { bg: 'bg-gray-500', border: 'border-gray-400', label: 'Neutral' },
    negative: { bg: 'bg-red-500', border: 'border-red-400', label: 'Negative' },
    mixed: { bg: 'bg-yellow-500', border: 'border-yellow-400', label: 'Mixed' },
  }

  // Calculate duration for display
  const duration = totalDuration || (progression.length > 0 ? Math.max(...progression.map(p => p.timestamp)) + 30 : 60)

  // Create segments based on sentiment progression
  const segments: Array<{
    sentiment: string
    startTime: number
    endTime: number
    trigger?: string
    widthPercent: number
  }> = []

  for (let i = 0; i < progression.length; i++) {
    const current = progression[i]
    const nextTimestamp = i < progression.length - 1 ? progression[i + 1].timestamp : duration
    const segmentDuration = nextTimestamp - current.timestamp
    const widthPercent = (segmentDuration / duration) * 100

    segments.push({
      sentiment: current.sentiment,
      startTime: current.timestamp,
      endTime: nextTimestamp,
      trigger: current.trigger,
      widthPercent: Math.max(widthPercent, 2), // Minimum 2% width for visibility
    })
  }

  const [hoveredSegment, setHoveredSegment] = useState<number | null>(null)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-text-primary">Sentiment Throughout Call</h3>
        <div className="flex gap-3">
          {Object.entries(sentimentColors).map(([key, value]) => (
            <div key={key} className="flex items-center gap-1">
              <div className={`w-3 h-3 rounded-full ${value.bg}`} />
              <span className="text-xs text-text-muted">{value.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline bar */}
      <div className="relative">
        <div className="flex h-8 rounded-lg overflow-hidden border border-border-primary">
          {segments.map((segment, index) => {
            const colors = sentimentColors[segment.sentiment] || sentimentColors.neutral
            return (
              <div
                key={index}
                className={`${colors.bg} relative cursor-pointer transition-opacity hover:opacity-80`}
                style={{ width: `${segment.widthPercent}%` }}
                onMouseEnter={() => setHoveredSegment(index)}
                onMouseLeave={() => setHoveredSegment(null)}
              >
                {/* Segment border */}
                {index > 0 && (
                  <div className="absolute left-0 top-0 bottom-0 w-px bg-bg-primary/50" />
                )}
              </div>
            )
          })}
        </div>

        {/* Tooltip */}
        {hoveredSegment !== null && segments[hoveredSegment] && (
          <div
            className="absolute z-10 top-full mt-2 bg-bg-tertiary border border-border-primary rounded-lg p-3 shadow-lg min-w-[200px]"
            style={{
              left: `${segments.slice(0, hoveredSegment).reduce((acc, s) => acc + s.widthPercent, 0) + segments[hoveredSegment].widthPercent / 2}%`,
              transform: 'translateX(-50%)'
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-3 h-3 rounded-full ${sentimentColors[segments[hoveredSegment].sentiment]?.bg || 'bg-gray-500'}`} />
              <span className="text-sm font-medium text-text-primary capitalize">
                {segments[hoveredSegment].sentiment}
              </span>
            </div>
            <p className="text-xs text-text-muted">
              {Math.floor(segments[hoveredSegment].startTime)}s - {Math.floor(segments[hoveredSegment].endTime)}s
            </p>
            {segments[hoveredSegment].trigger && (
              <p className="text-xs text-text-muted mt-1 italic">
                &quot;{segments[hoveredSegment].trigger}&quot;
              </p>
            )}
          </div>
        )}
      </div>

      {/* Time markers */}
      <div className="flex justify-between text-xs text-text-muted">
        <span>0:00</span>
        <span>{formatDuration(Math.floor(duration / 2))}</span>
        <span>{formatDuration(duration)}</span>
      </div>
    </div>
  )
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
      <div className="max-w-7xl mx-auto">
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
            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push(`/chat?context=call&callId=${call.id}`)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-primary text-white hover:bg-accent-primary/90 transition-colors text-sm font-medium"
              >
                <MessagesSquare className="w-4 h-4" />
                Chat about this call
              </button>
              <SentimentBadge sentiment={analytics?.overall_sentiment} size="lg" />
            </div>
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

        {/* Sentiment Timeline */}
        {analytics?.sentiment_progression && analytics.sentiment_progression.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="bg-bg-secondary rounded-xl border border-border-primary p-6 mb-6"
          >
            <SentimentTimeline
              progression={analytics.sentiment_progression}
              totalDuration={call.duration_seconds}
            />
          </motion.div>
        )}

        {/* Main Content - Transcript left, Analytics grid right */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Transcript - Narrower, scrollable */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2 bg-bg-secondary rounded-xl border border-border-primary p-4"
          >
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Transcript
              </h2>
              {call.recording_url && (
                <button className="flex items-center text-accent-primary hover:text-accent-primary/80 text-xs">
                  <Play className="w-3 h-3 mr-1" />
                  Play
                </button>
              )}
            </div>

            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
              {call.transcript && call.transcript.length > 0 ? (
                call.transcript.map((message, i) => {
                  const isAgent = message.role === 'assistant' || message.role === 'bot' || message.role === 'ai'
                  return (
                    <div key={i} className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
                      <div className={`max-w-[90%] p-2 rounded-lg ${isAgent ? 'bg-accent-primary/10' : 'bg-bg-tertiary'}`}>
                        <div className="flex items-center gap-1.5 mb-0.5">
                          {isAgent ? (
                            <Bot className="w-3 h-3 text-accent-primary" />
                          ) : (
                            <User className="w-3 h-3 text-text-muted" />
                          )}
                          <span className="text-[10px] font-medium text-text-muted uppercase">
                            {isAgent ? 'Agent' : 'Customer'}
                          </span>
                          {message.timestamp !== undefined && (
                            <span className="text-[10px] text-text-muted">{message.timestamp}s</span>
                          )}
                        </div>
                        <p className="text-xs text-text-primary leading-relaxed">{message.content}</p>
                      </div>
                    </div>
                  )
                })
              ) : (
                <p className="text-text-muted text-center py-8 text-sm">No transcript available</p>
              )}
            </div>
          </motion.div>

          {/* Analysis Panel - Wider, 2-column grid */}
          <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4 content-start">
            {/* Summary - spans full width */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="md:col-span-2 bg-bg-secondary rounded-xl border border-border-primary p-4"
            >
              <h2 className="text-sm font-semibold text-text-primary mb-2">Summary</h2>
              <p className="text-text-muted text-xs leading-relaxed">{analytics?.call_summary || 'No summary available'}</p>
            </motion.div>

            {/* Customer Intent */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-4"
            >
              <h2 className="text-sm font-semibold text-text-primary mb-2">Customer Intent</h2>
              <p className="text-text-muted text-xs leading-relaxed">{analytics?.customer_intent || 'Not identified'}</p>
            </motion.div>

            {/* Key Topics */}
            {analytics?.key_topics && analytics.key_topics.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <h2 className="text-sm font-semibold text-text-primary mb-2">Key Topics</h2>
                <div className="flex flex-wrap gap-1.5">
                  {analytics.key_topics.map((topic, i) => (
                    <span key={i} className="px-2 py-0.5 bg-bg-tertiary text-text-muted rounded-full text-xs">
                      {topic}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Agent Performance */}
            {analytics?.agent_performance_score !== undefined && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <h2 className="text-sm font-semibold text-text-primary mb-2">Agent Performance</h2>
                <div className="flex items-center">
                  <div className="flex-1 h-2 bg-bg-tertiary rounded-full overflow-hidden">
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
                  <span className="ml-2 font-semibold text-text-primary text-sm">
                    {analytics.agent_performance_score.toFixed(0)}/100
                  </span>
                </div>
              </motion.div>
            )}

            {/* Improvement Suggestions */}
            {analytics?.improvement_suggestions && analytics.improvement_suggestions.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-yellow-500/10 rounded-xl border border-yellow-500/30 p-4"
              >
                <h2 className="text-sm font-semibold text-yellow-400 mb-2 flex items-center gap-1.5">
                  <Lightbulb className="w-4 h-4" />
                  Improvements
                </h2>
                <ul className="space-y-1">
                  {analytics.improvement_suggestions.map((suggestion, i) => (
                    <li key={i} className="text-xs text-yellow-300/80 flex items-start">
                      <span className="mr-1.5">•</span>
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
                transition={{ delay: 0.45 }}
                className="bg-accent-primary/10 rounded-xl border border-accent-primary/30 p-4"
              >
                <h2 className="text-sm font-semibold text-accent-primary mb-2">Action Items</h2>
                <ul className="space-y-1">
                  {analytics.action_items.map((item, i) => (
                    <li key={i} className="text-xs text-text-muted flex items-start">
                      <CheckCircle className="w-3 h-3 mr-1.5 mt-0.5 flex-shrink-0 text-accent-primary" />
                      {item}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Customer Effort Score */}
            {analytics?.customer_effort_score !== undefined && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <h2 className="text-sm font-semibold text-text-primary mb-2">Customer Effort</h2>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xl font-bold ${
                    analytics.customer_effort_score <= 2 ? 'text-green-400' :
                    analytics.customer_effort_score === 3 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {analytics.customer_effort_score}/5
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    analytics.customer_effort_score <= 2 ? 'bg-green-500/20 text-green-400' :
                    analytics.customer_effort_score === 3 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {analytics.customer_effort_score <= 2 ? 'Effortless' :
                     analytics.customer_effort_score === 3 ? 'Moderate' : 'High Effort'}
                  </span>
                </div>
                <div className="space-y-0.5 text-xs text-text-muted">
                  {analytics.customer_had_to_repeat && (
                    <p className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-orange-400 rounded-full" />
                      Had to repeat info
                    </p>
                  )}
                  {analytics.transfer_count !== undefined && analytics.transfer_count > 0 && (
                    <p className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-orange-400 rounded-full" />
                      {analytics.transfer_count} transfer{analytics.transfer_count > 1 ? 's' : ''}
                    </p>
                  )}
                  {analytics.was_escalated && (
                    <p className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 bg-red-400 rounded-full" />
                      Escalated
                    </p>
                  )}
                </div>
              </motion.div>
            )}

            {/* Handle Time Breakdown */}
            {analytics?.handle_time_breakdown && (
              analytics.handle_time_breakdown.agent_talk_percentage !== undefined ||
              analytics.handle_time_breakdown.hold_time_seconds !== undefined
            ) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.55 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <h2 className="text-sm font-semibold text-text-primary mb-2">Talk Time</h2>
                <div className="space-y-2">
                  {analytics.handle_time_breakdown.agent_talk_percentage !== undefined && (
                    <div>
                      <div className="flex justify-between text-xs mb-0.5">
                        <span className="text-text-muted">Agent</span>
                        <span className="text-text-primary">{analytics.handle_time_breakdown.agent_talk_percentage?.toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${analytics.handle_time_breakdown.agent_talk_percentage}%` }} />
                      </div>
                    </div>
                  )}
                  {analytics.handle_time_breakdown.customer_talk_percentage !== undefined && (
                    <div>
                      <div className="flex justify-between text-xs mb-0.5">
                        <span className="text-text-muted">Customer</span>
                        <span className="text-text-primary">{analytics.handle_time_breakdown.customer_talk_percentage?.toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                        <div className="h-full bg-purple-500 rounded-full" style={{ width: `${analytics.handle_time_breakdown.customer_talk_percentage}%` }} />
                      </div>
                    </div>
                  )}
                  {analytics.handle_time_breakdown.hold_time_seconds !== undefined && analytics.handle_time_breakdown.hold_time_seconds > 0 && (
                    <p className="text-xs text-text-muted pt-1 border-t border-border-primary">
                      Hold: <span className="text-text-primary">{formatDuration(analytics.handle_time_breakdown.hold_time_seconds)}</span>
                    </p>
                  )}
                </div>
              </motion.div>
            )}

            {/* Conversation Quality */}
            {analytics?.conversation_quality && (
              analytics.conversation_quality.clarity_score !== undefined ||
              analytics.conversation_quality.empathy_phrases_count !== undefined
            ) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="bg-bg-secondary rounded-xl border border-border-primary p-4"
              >
                <h2 className="text-sm font-semibold text-text-primary mb-2">Conversation Quality</h2>
                <div className="grid grid-cols-2 gap-2">
                  {analytics.conversation_quality.clarity_score !== undefined && (
                    <div className="text-center p-1.5 bg-bg-tertiary rounded-lg">
                      <p className={`text-lg font-bold ${
                        analytics.conversation_quality.clarity_score >= 80 ? 'text-green-400' :
                        analytics.conversation_quality.clarity_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {analytics.conversation_quality.clarity_score.toFixed(0)}
                      </p>
                      <p className="text-[10px] text-text-muted">Clarity</p>
                    </div>
                  )}
                  {analytics.conversation_quality.empathy_phrases_count !== undefined && (
                    <div className="text-center p-1.5 bg-bg-tertiary rounded-lg">
                      <p className="text-lg font-bold text-pink-400">{analytics.conversation_quality.empathy_phrases_count}</p>
                      <p className="text-[10px] text-text-muted">Empathy</p>
                    </div>
                  )}
                  {analytics.conversation_quality.jargon_usage_count !== undefined && (
                    <div className="text-center p-1.5 bg-bg-tertiary rounded-lg">
                      <p className="text-lg font-bold text-yellow-400">{analytics.conversation_quality.jargon_usage_count}</p>
                      <p className="text-[10px] text-text-muted">Jargon</p>
                    </div>
                  )}
                  {analytics.conversation_quality.avg_agent_response_time_seconds !== undefined && (
                    <div className="text-center p-1.5 bg-bg-tertiary rounded-lg">
                      <p className="text-lg font-bold text-text-primary">{analytics.conversation_quality.avg_agent_response_time_seconds.toFixed(1)}s</p>
                      <p className="text-[10px] text-text-muted">Avg Response</p>
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Competitive Intelligence */}
            {analytics?.competitive_intelligence && (
              (analytics.competitive_intelligence.competitors_mentioned?.length ?? 0) > 0 ||
              analytics.competitive_intelligence.switching_intent_detected
            ) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.65 }}
                className="bg-cyan-500/10 rounded-xl border border-cyan-500/30 p-4"
              >
                <h2 className="text-sm font-semibold text-cyan-400 mb-2">Competitive Intel</h2>
                {analytics.competitive_intelligence.competitors_mentioned && analytics.competitive_intelligence.competitors_mentioned.length > 0 && (
                  <div className="mb-2">
                    <p className="text-[10px] text-text-muted mb-1">Competitors:</p>
                    <div className="flex flex-wrap gap-1">
                      {analytics.competitive_intelligence.competitors_mentioned.map((comp, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-[10px]">{comp}</span>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.competitive_intelligence.switching_intent_detected && (
                  <p className="text-xs text-red-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Switching intent
                  </p>
                )}
                {analytics.competitive_intelligence.price_sensitivity_level && analytics.competitive_intelligence.price_sensitivity_level !== 'none' && (
                  <p className="text-xs text-text-muted">
                    Price: <span className="capitalize text-yellow-400">{analytics.competitive_intelligence.price_sensitivity_level}</span>
                  </p>
                )}
              </motion.div>
            )}

            {/* Product Analytics */}
            {analytics?.product_analytics && (
              (analytics.product_analytics.products_discussed?.length ?? 0) > 0 ||
              (analytics.product_analytics.features_requested?.length ?? 0) > 0 ||
              analytics.product_analytics.upsell_opportunity_detected
            ) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="bg-green-500/10 rounded-xl border border-green-500/30 p-4"
              >
                <h2 className="text-sm font-semibold text-green-400 mb-2">Product Insights</h2>
                {analytics.product_analytics.products_discussed && analytics.product_analytics.products_discussed.length > 0 && (
                  <div className="mb-1.5">
                    <p className="text-[10px] text-text-muted mb-0.5">Products:</p>
                    <div className="flex flex-wrap gap-1">
                      {analytics.product_analytics.products_discussed.map((prod, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px]">{prod}</span>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.product_analytics.features_requested && analytics.product_analytics.features_requested.length > 0 && (
                  <div className="mb-1.5">
                    <p className="text-[10px] text-text-muted mb-0.5">Requested:</p>
                    <div className="flex flex-wrap gap-1">
                      {analytics.product_analytics.features_requested.map((feat, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded text-[10px]">{feat}</span>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.product_analytics.features_problematic && analytics.product_analytics.features_problematic.length > 0 && (
                  <div className="mb-1.5">
                    <p className="text-[10px] text-text-muted mb-0.5">Issues:</p>
                    <div className="flex flex-wrap gap-1">
                      {analytics.product_analytics.features_problematic.map((feat, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded text-[10px]">{feat}</span>
                      ))}
                    </div>
                  </div>
                )}
                {analytics.product_analytics.upsell_opportunity_detected && (
                  <p className="text-xs text-green-400 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" />
                    Upsell opportunity
                  </p>
                )}
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
    </AuthenticatedLayout>
  )
}
