'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Clock,
  TrendingUp,
  Users,
  Building2,
  Target,
  MessageSquare,
  Package,
  AlertTriangle,
  Gauge,
  BarChart3,
  RefreshCw,
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { useOnboardingStore } from '@/stores/onboarding-store'

interface TimeBasedData {
  hourly_distribution: Record<number, { calls: number; avg_sentiment: number }>
  day_of_week_distribution: Record<string, { calls: number; avg_duration: number }>
  peak_hours: Array<{ hour: number; calls: number }>
  total_calls: number
}

interface EffortScoreData {
  ces_distribution: Record<number, number>
  average_ces: number
  repeat_rate_percent: number
  average_transfers: number
  ces_breakdown: {
    effortless: number
    moderate: number
    high_effort: number
  }
  total_calls: number
}

interface EscalationData {
  total_calls: number
  escalated_calls: number
  escalation_rate_percent: number
  escalation_resolution_rate_percent: number
  escalation_levels: Record<string, number>
  top_escalation_reasons: Array<{ reason: string; count: number }>
  top_departments: Array<{ department: string; count: number }>
}

interface CompetitiveData {
  total_calls: number
  calls_with_competitor_mentions: number
  competitor_mention_rate_percent: number
  switching_intent_rate_percent: number
  top_competitors: Array<{ name: string; mentions: number }>
  price_sensitivity_distribution: Record<string, number>
}

interface ProductData {
  total_calls: number
  upsell_opportunities: number
  upsell_opportunity_rate_percent: number
  top_products_discussed: Array<{ product: string; mentions: number }>
  top_features_requested: Array<{ feature: string; requests: number }>
  top_problematic_features: Array<{ feature: string; issues: number }>
}

interface ConversationQualityData {
  total_calls: number
  average_clarity_score: number
  average_empathy_phrases: number
  average_jargon_usage: number
  average_response_time_seconds: number
  average_agent_talk_percentage: number
  average_hold_time_seconds: number
  calls_with_high_clarity: number
  calls_with_low_clarity: number
}

function formatHour(hour: number): string {
  if (hour === 0) return '12 AM'
  if (hour === 12) return '12 PM'
  if (hour < 12) return `${hour} AM`
  return `${hour - 12} PM`
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function getCESLabel(score: number): string {
  if (score <= 2) return 'Effortless'
  if (score === 3) return 'Moderate'
  return 'High Effort'
}

function getCESColor(score: number): string {
  if (score <= 2) return 'text-green-400'
  if (score === 3) return 'text-yellow-400'
  return 'text-red-400'
}

export default function AdvancedAnalyticsPage() {
  const { token } = useOnboardingStore()
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState(30)

  const [timeBased, setTimeBased] = useState<TimeBasedData | null>(null)
  const [effortScore, setEffortScore] = useState<EffortScoreData | null>(null)
  const [escalation, setEscalation] = useState<EscalationData | null>(null)
  const [competitive, setCompetitive] = useState<CompetitiveData | null>(null)
  const [product, setProduct] = useState<ProductData | null>(null)
  const [conversationQuality, setConversationQuality] = useState<ConversationQualityData | null>(null)

  const loadData = async () => {
    if (!token) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      const [timeResult, effortResult, escalationResult, competitiveResult, productResult, qualityResult] = await Promise.all([
        api.getTimeBasedAnalytics(token, dateRange).catch(() => null),
        api.getEffortScoreAnalytics(token, dateRange).catch(() => null),
        api.getEscalationAnalytics(token, dateRange).catch(() => null),
        api.getCompetitiveIntelligence(token, dateRange).catch(() => null),
        api.getProductAnalytics(token, dateRange).catch(() => null),
        api.getConversationQualityAnalytics(token, dateRange).catch(() => null),
      ])
      setTimeBased(timeResult)
      setEffortScore(effortResult)
      setEscalation(escalationResult)
      setCompetitive(competitiveResult)
      setProduct(productResult)
      setConversationQuality(qualityResult)
    } catch (e) {
      console.error('Failed to load advanced analytics:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [token, dateRange])

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="min-h-screen bg-bg-primary flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
        </div>
      </AuthenticatedLayout>
    )
  }

  return (
    <AuthenticatedLayout>
      <div className="min-h-screen bg-bg-primary p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="p-2 hover:bg-bg-secondary rounded-lg transition-colors">
                <ArrowLeft className="w-5 h-5 text-text-muted" />
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-text-primary">Advanced Analytics</h1>
                <p className="text-text-muted text-sm">Deep insights from your customer conversations</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={dateRange}
                onChange={(e) => setDateRange(Number(e.target.value))}
                className="bg-bg-secondary border border-border-primary rounded-lg px-3 py-2 text-sm text-text-primary"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <button
                onClick={loadData}
                className="p-2 bg-bg-secondary border border-border-primary rounded-lg hover:bg-bg-tertiary transition-colors"
              >
                <RefreshCw className="w-4 h-4 text-text-muted" />
              </button>
            </div>
          </div>

          {/* Customer Effort Score Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-bg-secondary rounded-xl border border-border-primary p-6 mb-6"
          >
            <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Gauge className="w-5 h-5 text-blue-400" />
              Customer Effort Score (CES)
            </h2>
            {effortScore ? (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {/* Average CES */}
                <div className="text-center">
                  <p className="text-xs text-text-muted mb-1">Average CES</p>
                  <p className={`text-3xl font-bold ${getCESColor(effortScore.average_ces)}`}>
                    {effortScore.average_ces.toFixed(1)}
                  </p>
                  <p className="text-xs text-text-muted">{getCESLabel(effortScore.average_ces)}</p>
                </div>

                {/* CES Distribution */}
                <div className="col-span-2">
                  <p className="text-xs text-text-muted mb-2">Distribution (1=Effortless, 5=High Effort)</p>
                  <div className="flex items-end gap-2 h-20">
                    {[1, 2, 3, 4, 5].map((score) => {
                      const count = effortScore.ces_distribution[score] || 0
                      const maxCount = Math.max(...Object.values(effortScore.ces_distribution), 1)
                      const height = Math.max(10, (count / maxCount) * 100)
                      return (
                        <div key={score} className="flex-1 flex flex-col items-center">
                          <div
                            className={`w-full rounded-t ${
                              score <= 2 ? 'bg-green-500' : score === 3 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ height: `${height}%` }}
                          />
                          <span className="text-xs text-text-muted mt-1">{score}</span>
                          <span className="text-xs text-text-muted">{count}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* CES Breakdown */}
                <div>
                  <p className="text-xs text-text-muted mb-2">Breakdown</p>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-green-400">Effortless</span>
                      <span className="text-sm font-medium text-text-primary">{effortScore.ces_breakdown.effortless}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-yellow-400">Moderate</span>
                      <span className="text-sm font-medium text-text-primary">{effortScore.ces_breakdown.moderate}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-red-400">High Effort</span>
                      <span className="text-sm font-medium text-text-primary">{effortScore.ces_breakdown.high_effort}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-text-muted text-sm">No CES data available</p>
            )}
          </motion.div>

          {/* Time-Based & Escalation Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Peak Hours */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-purple-400" />
                Call Volume by Hour
              </h2>
              {timeBased && Object.keys(timeBased.hourly_distribution).length > 0 ? (
                <div>
                  <div className="flex items-end gap-1 h-32 mb-4">
                    {Object.entries(timeBased.hourly_distribution).map(([hour, data]) => {
                      const maxCalls = Math.max(...Object.values(timeBased.hourly_distribution).map(d => d.calls), 1)
                      const height = Math.max(4, (data.calls / maxCalls) * 100)
                      const isPeak = timeBased.peak_hours.some(p => p.hour === parseInt(hour))
                      return (
                        <div
                          key={hour}
                          className={`flex-1 rounded-t ${isPeak ? 'bg-purple-500' : 'bg-purple-500/40'}`}
                          style={{ height: `${height}%` }}
                          title={`${formatHour(parseInt(hour))}: ${data.calls} calls`}
                        />
                      )
                    })}
                  </div>
                  <div className="flex justify-between text-xs text-text-muted">
                    <span>12 AM</span>
                    <span>6 AM</span>
                    <span>12 PM</span>
                    <span>6 PM</span>
                    <span>11 PM</span>
                  </div>
                  <div className="mt-4">
                    <p className="text-xs text-text-muted mb-2">Peak Hours:</p>
                    <div className="flex flex-wrap gap-2">
                      {timeBased.peak_hours.map((peak) => (
                        <span key={peak.hour} className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs">
                          {formatHour(peak.hour)} ({peak.calls} calls)
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-text-muted text-sm">No time-based data available</p>
              )}
            </motion.div>

            {/* Escalation Analytics */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-orange-400" />
                Escalation Analytics
              </h2>
              {escalation ? (
                <div>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="text-center p-3 bg-bg-tertiary rounded-lg">
                      <p className="text-2xl font-bold text-orange-400">{escalation.escalation_rate_percent.toFixed(1)}%</p>
                      <p className="text-xs text-text-muted">Escalation Rate</p>
                    </div>
                    <div className="text-center p-3 bg-bg-tertiary rounded-lg">
                      <p className="text-2xl font-bold text-green-400">{escalation.escalation_resolution_rate_percent.toFixed(1)}%</p>
                      <p className="text-xs text-text-muted">Resolution Rate</p>
                    </div>
                  </div>
                  {escalation.top_escalation_reasons.length > 0 && (
                    <div>
                      <p className="text-xs text-text-muted mb-2">Top Escalation Reasons:</p>
                      <div className="space-y-2">
                        {escalation.top_escalation_reasons.slice(0, 5).map((reason, i) => (
                          <div key={i} className="flex justify-between items-center">
                            <span className="text-sm text-text-muted truncate flex-1">{reason.reason}</span>
                            <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded ml-2">{reason.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-text-muted text-sm">No escalation data available</p>
              )}
            </motion.div>
          </div>

          {/* Competitive Intelligence & Product Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Competitive Intelligence */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-cyan-400" />
                Competitive Intelligence
              </h2>
              {competitive ? (
                <div>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="text-center p-3 bg-bg-tertiary rounded-lg">
                      <p className="text-2xl font-bold text-cyan-400">{competitive.competitor_mention_rate_percent.toFixed(1)}%</p>
                      <p className="text-xs text-text-muted">Competitor Mention Rate</p>
                    </div>
                    <div className="text-center p-3 bg-bg-tertiary rounded-lg">
                      <p className="text-2xl font-bold text-red-400">{competitive.switching_intent_rate_percent.toFixed(1)}%</p>
                      <p className="text-xs text-text-muted">Switching Intent</p>
                    </div>
                  </div>
                  {competitive.top_competitors.length > 0 ? (
                    <div>
                      <p className="text-xs text-text-muted mb-2">Top Competitors Mentioned:</p>
                      <div className="space-y-2">
                        {competitive.top_competitors.slice(0, 5).map((comp, i) => (
                          <div key={i} className="flex justify-between items-center">
                            <span className="text-sm text-text-muted">{comp.name}</span>
                            <span className="text-xs bg-cyan-500/20 text-cyan-400 px-2 py-1 rounded">{comp.mentions}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-text-muted text-sm">No competitors mentioned yet</p>
                  )}
                </div>
              ) : (
                <p className="text-text-muted text-sm">No competitive data available</p>
              )}
            </motion.div>

            {/* Product Analytics */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Package className="w-5 h-5 text-green-400" />
                Product Analytics
              </h2>
              {product ? (
                <div>
                  <div className="flex items-center justify-between mb-4 p-3 bg-bg-tertiary rounded-lg">
                    <div>
                      <p className="text-xs text-text-muted">Upsell Opportunities</p>
                      <p className="text-xl font-bold text-green-400">{product.upsell_opportunities}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-text-muted">Rate</p>
                      <p className="text-xl font-bold text-text-primary">{product.upsell_opportunity_rate_percent.toFixed(1)}%</p>
                    </div>
                  </div>
                  {product.top_features_requested.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-text-muted mb-2">Top Feature Requests:</p>
                      <div className="flex flex-wrap gap-2">
                        {product.top_features_requested.slice(0, 5).map((feature, i) => (
                          <span key={i} className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                            {feature.feature} ({feature.requests})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {product.top_problematic_features.length > 0 && (
                    <div>
                      <p className="text-xs text-text-muted mb-2">Problematic Features:</p>
                      <div className="flex flex-wrap gap-2">
                        {product.top_problematic_features.slice(0, 5).map((feature, i) => (
                          <span key={i} className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                            {feature.feature} ({feature.issues})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-text-muted text-sm">No product data available</p>
              )}
            </motion.div>
          </div>

          {/* Conversation Quality Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-bg-secondary rounded-xl border border-border-primary p-6 mb-6"
          >
            <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-indigo-400" />
              Conversation Quality Metrics
            </h2>
            {conversationQuality ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-indigo-400">{conversationQuality.average_clarity_score.toFixed(0)}</p>
                  <p className="text-xs text-text-muted">Clarity Score</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-pink-400">{conversationQuality.average_empathy_phrases.toFixed(1)}</p>
                  <p className="text-xs text-text-muted">Avg Empathy Phrases</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-yellow-400">{conversationQuality.average_jargon_usage.toFixed(1)}</p>
                  <p className="text-xs text-text-muted">Avg Jargon Usage</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-text-primary">{conversationQuality.average_response_time_seconds.toFixed(1)}s</p>
                  <p className="text-xs text-text-muted">Avg Response Time</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-blue-400">{conversationQuality.average_agent_talk_percentage.toFixed(0)}%</p>
                  <p className="text-xs text-text-muted">Agent Talk %</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-orange-400">{formatDuration(conversationQuality.average_hold_time_seconds)}</p>
                  <p className="text-xs text-text-muted">Avg Hold Time</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-green-400">{conversationQuality.calls_with_high_clarity}</p>
                  <p className="text-xs text-text-muted">High Clarity Calls</p>
                </div>
                <div className="text-center p-4 bg-bg-tertiary rounded-lg">
                  <p className="text-2xl font-bold text-red-400">{conversationQuality.calls_with_low_clarity}</p>
                  <p className="text-xs text-text-muted">Low Clarity Calls</p>
                </div>
              </div>
            ) : (
              <p className="text-text-muted text-sm">No conversation quality data available</p>
            )}
          </motion.div>

          {/* Day of Week Distribution */}
          {timeBased && Object.keys(timeBased.day_of_week_distribution).length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="bg-bg-secondary rounded-xl border border-border-primary p-6"
            >
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-teal-400" />
                Call Volume by Day of Week
              </h2>
              <div className="grid grid-cols-7 gap-2">
                {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => {
                  const data = timeBased.day_of_week_distribution[day] || { calls: 0, avg_duration: 0 }
                  const maxCalls = Math.max(...Object.values(timeBased.day_of_week_distribution).map(d => d.calls), 1)
                  const intensity = Math.min(100, (data.calls / maxCalls) * 100)
                  return (
                    <div key={day} className="text-center">
                      <div
                        className="h-16 rounded-lg mb-2 flex items-center justify-center"
                        style={{ backgroundColor: `rgba(45, 212, 191, ${intensity / 100 * 0.7 + 0.1})` }}
                      >
                        <span className="text-lg font-bold text-white">{data.calls}</span>
                      </div>
                      <p className="text-xs text-text-muted">{day.slice(0, 3)}</p>
                      <p className="text-xs text-text-muted/60">{formatDuration(data.avg_duration)} avg</p>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </AuthenticatedLayout>
  )
}
