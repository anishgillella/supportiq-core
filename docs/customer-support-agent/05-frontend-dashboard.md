# Phase 5: Frontend Dashboard

## Overview

This document details the frontend implementation for:
1. Analytics Dashboard (`/dashboard`)
2. Call Detail Page (`/dashboard/calls/[id]`)
3. Voice Call Widget (click-to-call button)

## File Structure

```
frontend/src/
├── app/
│   └── dashboard/
│       ├── page.tsx              # Main dashboard
│       ├── layout.tsx            # Dashboard layout
│       └── calls/
│           └── [id]/
│               └── page.tsx      # Call detail page
├── components/
│   └── voice/
│       ├── VoiceWidget.tsx       # Click-to-call button
│       ├── CallCard.tsx          # Call list item
│       ├── TranscriptViewer.tsx  # Transcript display
│       ├── SentimentBadge.tsx    # Sentiment indicator
│       ├── StatsCard.tsx         # Stats card component
│       └── charts/
│           ├── SentimentChart.tsx
│           ├── CategoryChart.tsx
│           └── TrendChart.tsx
├── hooks/
│   └── useVapi.ts                # VAPI SDK hook
└── lib/
    └── api/
        └── voice.ts              # API client functions
```

## 1. API Client (`lib/api/voice.ts`)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Call {
  id: string;
  vapi_call_id: string;
  started_at: string;
  ended_at?: string;
  duration_seconds?: number;
  status: string;
  agent_type: string;
  sentiment?: string;
  category?: string;
  resolution?: string;
}

export interface CallDetail extends Call {
  transcript?: Array<{
    role: string;
    content: string;
    timestamp?: number;
  }>;
  analytics?: {
    overall_sentiment: string;
    sentiment_score: number;
    sentiment_progression: Array<{ timestamp: number; sentiment: string }>;
    primary_category: string;
    secondary_categories: string[];
    resolution_status: string;
    customer_satisfaction_predicted: number;
    agent_performance_score: number;
    customer_intent: string;
    key_topics: string[];
    action_items: string[];
    improvement_suggestions: string[];
    call_summary: string;
  };
  recording_url?: string;
}

export interface DashboardData {
  overview: {
    total_calls: number;
    avg_duration_seconds: number;
    resolution_rate: number;
    avg_sentiment_score: number;
    calls_today: number;
    calls_this_week: number;
  };
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
    mixed: number;
  };
  categories: {
    categories: Record<string, number>;
  };
  trends: Array<{
    date: string;
    calls: number;
    avg_sentiment: number;
    resolution_rate: number;
  }>;
  top_issues: Array<{ category: string; count: number }>;
  recent_calls: Array<{
    id: string;
    started_at: string;
    duration?: number;
    status: string;
    sentiment?: string;
  }>;
}

export async function fetchDashboard(days: number = 7): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/api/v1/analytics/dashboard?days=${days}`);
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function fetchCalls(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  sentiment?: string;
}): Promise<{ calls: Call[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', params.page.toString());
  if (params?.pageSize) query.set('page_size', params.pageSize.toString());
  if (params?.status) query.set('status', params.status);
  if (params?.sentiment) query.set('sentiment', params.sentiment);

  const res = await fetch(`${API_BASE}/api/v1/voice/calls?${query}`);
  if (!res.ok) throw new Error('Failed to fetch calls');
  return res.json();
}

export async function fetchCallDetail(callId: string): Promise<CallDetail> {
  const res = await fetch(`${API_BASE}/api/v1/voice/calls/${callId}`);
  if (!res.ok) throw new Error('Failed to fetch call');
  return res.json();
}
```

## 2. VAPI Hook (`hooks/useVapi.ts`)

```typescript
'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Vapi from '@vapi-ai/web';

interface UseVapiOptions {
  publicKey: string;
  assistantId: string;
  onCallStart?: () => void;
  onCallEnd?: () => void;
  onMessage?: (message: any) => void;
  onError?: (error: any) => void;
}

interface VapiState {
  isConnected: boolean;
  isCallActive: boolean;
  isMuted: boolean;
  volume: number;
}

export function useVapi(options: UseVapiOptions) {
  const vapiRef = useRef<Vapi | null>(null);
  const [state, setState] = useState<VapiState>({
    isConnected: false,
    isCallActive: false,
    isMuted: false,
    volume: 1,
  });

  useEffect(() => {
    // Initialize VAPI
    const vapi = new Vapi(options.publicKey);
    vapiRef.current = vapi;

    // Set up event listeners
    vapi.on('call-start', () => {
      setState(s => ({ ...s, isCallActive: true }));
      options.onCallStart?.();
    });

    vapi.on('call-end', () => {
      setState(s => ({ ...s, isCallActive: false }));
      options.onCallEnd?.();
    });

    vapi.on('message', (message) => {
      options.onMessage?.(message);
    });

    vapi.on('error', (error) => {
      console.error('VAPI error:', error);
      options.onError?.(error);
    });

    setState(s => ({ ...s, isConnected: true }));

    return () => {
      vapi.stop();
    };
  }, [options.publicKey]);

  const startCall = useCallback(async () => {
    if (!vapiRef.current) return;

    try {
      await vapiRef.current.start(options.assistantId);
    } catch (error) {
      console.error('Failed to start call:', error);
      options.onError?.(error);
    }
  }, [options.assistantId]);

  const endCall = useCallback(() => {
    if (!vapiRef.current) return;
    vapiRef.current.stop();
  }, []);

  const toggleMute = useCallback(() => {
    if (!vapiRef.current) return;

    const newMuted = !state.isMuted;
    vapiRef.current.setMuted(newMuted);
    setState(s => ({ ...s, isMuted: newMuted }));
  }, [state.isMuted]);

  return {
    ...state,
    startCall,
    endCall,
    toggleMute,
  };
}
```

## 3. Voice Widget Component (`components/voice/VoiceWidget.tsx`)

```tsx
'use client';

import { useState } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Loader2 } from 'lucide-react';
import { useVapi } from '@/hooks/useVapi';

interface VoiceWidgetProps {
  publicKey: string;
  assistantId: string;
}

export function VoiceWidget({ publicKey, assistantId }: VoiceWidgetProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);

  const {
    isConnected,
    isCallActive,
    isMuted,
    startCall,
    endCall,
    toggleMute,
  } = useVapi({
    publicKey,
    assistantId,
    onCallStart: () => setIsLoading(false),
    onCallEnd: () => {
      setIsLoading(false);
      // Optionally clear messages or keep for review
    },
    onMessage: (message) => {
      if (message.type === 'transcript') {
        setMessages(prev => [...prev, {
          role: message.role,
          content: message.transcript,
        }]);
      }
    },
    onError: () => setIsLoading(false),
  });

  const handleStartCall = async () => {
    setIsLoading(true);
    setMessages([]);
    await startCall();
  };

  const handleEndCall = () => {
    endCall();
  };

  if (!isConnected) {
    return (
      <div className="fixed bottom-6 right-6 bg-gray-800 text-white px-4 py-3 rounded-full shadow-lg">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 flex flex-col items-end gap-3">
      {/* Live Transcript (when call active) */}
      {isCallActive && messages.length > 0 && (
        <div className="bg-white rounded-lg shadow-xl p-4 w-80 max-h-60 overflow-y-auto">
          <h4 className="text-sm font-semibold text-gray-600 mb-2">Live Transcript</h4>
          <div className="space-y-2">
            {messages.slice(-5).map((msg, i) => (
              <div
                key={i}
                className={`text-sm ${
                  msg.role === 'assistant' ? 'text-blue-600' : 'text-gray-800'
                }`}
              >
                <span className="font-medium">
                  {msg.role === 'assistant' ? 'Agent: ' : 'You: '}
                </span>
                {msg.content}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Call Controls */}
      <div className="flex items-center gap-2">
        {isCallActive && (
          <button
            onClick={toggleMute}
            className={`p-3 rounded-full shadow-lg transition-colors ${
              isMuted
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-gray-700 hover:bg-gray-600'
            } text-white`}
          >
            {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
        )}

        <button
          onClick={isCallActive ? handleEndCall : handleStartCall}
          disabled={isLoading}
          className={`p-4 rounded-full shadow-lg transition-all ${
            isCallActive
              ? 'bg-red-500 hover:bg-red-600 animate-pulse'
              : 'bg-green-500 hover:bg-green-600'
          } text-white`}
        >
          {isLoading ? (
            <Loader2 className="w-6 h-6 animate-spin" />
          ) : isCallActive ? (
            <PhoneOff className="w-6 h-6" />
          ) : (
            <Phone className="w-6 h-6" />
          )}
        </button>
      </div>

      {/* Status Label */}
      <span className="text-xs text-gray-500">
        {isLoading
          ? 'Connecting...'
          : isCallActive
          ? 'Call in progress'
          : 'Click to call support'}
      </span>
    </div>
  );
}
```

## 4. Dashboard Page (`app/dashboard/page.tsx`)

```tsx
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Phone,
  Clock,
  CheckCircle,
  TrendingUp,
  AlertCircle,
  Smile,
  Meh,
  Frown,
} from 'lucide-react';
import { fetchDashboard, DashboardData } from '@/lib/api/voice';
import { StatsCard } from '@/components/voice/StatsCard';
import { SentimentBadge } from '@/components/voice/SentimentBadge';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState(7);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const result = await fetchDashboard(dateRange);
        setData(result);
      } catch (e) {
        setError('Failed to load dashboard');
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [dateRange]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-gray-600">{error || 'No data available'}</p>
      </div>
    );
  }

  const { overview, sentiment, categories, trends, top_issues, recent_calls } = data;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Voice Analytics</h1>
            <p className="text-gray-500">Customer call insights and performance metrics</p>
          </div>

          <select
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="px-4 py-2 border rounded-lg bg-white"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
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
            value={formatSentiment(overview.avg_sentiment_score)}
            icon={<TrendingUp className="w-6 h-6" />}
            color={overview.avg_sentiment_score > 0 ? 'green' : overview.avg_sentiment_score < 0 ? 'red' : 'gray'}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sentiment Breakdown */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Breakdown</h2>
            <div className="space-y-4">
              <SentimentRow
                icon={<Smile className="w-5 h-5 text-green-500" />}
                label="Positive"
                count={sentiment.positive}
                total={overview.total_calls}
                color="green"
              />
              <SentimentRow
                icon={<Meh className="w-5 h-5 text-gray-500" />}
                label="Neutral"
                count={sentiment.neutral}
                total={overview.total_calls}
                color="gray"
              />
              <SentimentRow
                icon={<Frown className="w-5 h-5 text-red-500" />}
                label="Negative"
                count={sentiment.negative}
                total={overview.total_calls}
                color="red"
              />
            </div>
          </div>

          {/* Top Issues */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Issue Categories</h2>
            <div className="space-y-3">
              {top_issues.map((issue, i) => (
                <div key={i} className="flex justify-between items-center">
                  <span className="text-gray-700 capitalize">
                    {issue.category.replace(/_/g, ' ')}
                  </span>
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                    {issue.count}
                  </span>
                </div>
              ))}
              {top_issues.length === 0 && (
                <p className="text-gray-400 text-sm">No data yet</p>
              )}
            </div>
          </div>

          {/* Recent Calls */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Recent Calls</h2>
              <Link href="/dashboard/calls" className="text-blue-500 text-sm hover:underline">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              {recent_calls.map((call) => (
                <Link
                  key={call.id}
                  href={`/dashboard/calls/${call.id}`}
                  className="block p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-gray-600">
                        {new Date(call.started_at).toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-400">
                        {call.duration ? formatDuration(call.duration) : 'N/A'}
                      </p>
                    </div>
                    <SentimentBadge sentiment={call.sentiment} />
                  </div>
                </Link>
              ))}
              {recent_calls.length === 0 && (
                <p className="text-gray-400 text-sm">No calls yet</p>
              )}
            </div>
          </div>
        </div>

        {/* Trends Chart (placeholder) */}
        <div className="mt-8 bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Call Volume Trend</h2>
          <div className="h-64 flex items-end justify-between gap-2">
            {trends.map((day, i) => (
              <div key={i} className="flex-1 flex flex-col items-center">
                <div
                  className="w-full bg-blue-500 rounded-t"
                  style={{
                    height: `${Math.max(10, (day.calls / Math.max(...trends.map(t => t.calls))) * 200)}px`
                  }}
                />
                <span className="text-xs text-gray-500 mt-2">
                  {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper Components

function SentimentRow({
  icon,
  label,
  count,
  total,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      {icon}
      <div className="flex-1">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">{label}</span>
          <span className="text-gray-900 font-medium">{count}</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full bg-${color}-500 rounded-full`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// Helpers

function formatDuration(seconds: number): string {
  if (!seconds) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatSentiment(score: number): string {
  if (score > 0.3) return 'Positive';
  if (score < -0.3) return 'Negative';
  return 'Neutral';
}
```

## 5. Call Detail Page (`app/dashboard/calls/[id]/page.tsx`)

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
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
} from 'lucide-react';
import { fetchCallDetail, CallDetail } from '@/lib/api/voice';
import { SentimentBadge } from '@/components/voice/SentimentBadge';

export default function CallDetailPage() {
  const params = useParams();
  const callId = params.id as string;

  const [call, setCall] = useState<CallDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const result = await fetchCallDetail(callId);
        setCall(result);
      } catch (e) {
        setError('Failed to load call');
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [callId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !call) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <p className="text-gray-600">{error || 'Call not found'}</p>
        <Link href="/dashboard" className="mt-4 text-blue-500 hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const analytics = call.analytics;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Back Button */}
        <Link
          href="/dashboard"
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>

        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Call Details</h1>
              <p className="text-gray-500">
                {new Date(call.started_at).toLocaleString()}
              </p>
            </div>
            <SentimentBadge sentiment={analytics?.overall_sentiment} size="lg" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div>
              <p className="text-sm text-gray-500">Duration</p>
              <p className="text-lg font-semibold">
                {call.duration_seconds
                  ? `${Math.floor(call.duration_seconds / 60)}:${(call.duration_seconds % 60).toString().padStart(2, '0')}`
                  : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Category</p>
              <p className="text-lg font-semibold capitalize">
                {analytics?.primary_category?.replace(/_/g, ' ') || 'Unknown'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Resolution</p>
              <p className="text-lg font-semibold capitalize flex items-center">
                {analytics?.resolution_status === 'resolved' ? (
                  <CheckCircle className="w-5 h-5 text-green-500 mr-1" />
                ) : analytics?.resolution_status === 'escalated' ? (
                  <AlertTriangle className="w-5 h-5 text-yellow-500 mr-1" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500 mr-1" />
                )}
                {analytics?.resolution_status?.replace(/_/g, ' ') || 'Unknown'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">CSAT Predicted</p>
              <p className="text-lg font-semibold">
                {analytics?.customer_satisfaction_predicted?.toFixed(1) || 'N/A'} / 5.0
              </p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Transcript */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Transcript</h2>
              {call.recording_url && (
                <button className="flex items-center text-blue-500 hover:text-blue-600">
                  <Play className="w-4 h-4 mr-1" />
                  Play Recording
                </button>
              )}
            </div>

            <div className="space-y-4 max-h-[500px] overflow-y-auto">
              {call.transcript?.map((message, i) => (
                <div
                  key={i}
                  className={`flex ${
                    message.role === 'assistant' || message.role === 'bot'
                      ? 'justify-start'
                      : 'justify-end'
                  }`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-lg ${
                      message.role === 'assistant' || message.role === 'bot'
                        ? 'bg-blue-50 text-blue-900'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {message.role === 'assistant' || message.role === 'bot' ? (
                        <Bot className="w-4 h-4 text-blue-500" />
                      ) : (
                        <User className="w-4 h-4 text-gray-500" />
                      )}
                      <span className="text-xs font-medium uppercase">
                        {message.role === 'assistant' || message.role === 'bot'
                          ? 'Agent'
                          : 'Customer'}
                      </span>
                      {message.timestamp !== undefined && (
                        <span className="text-xs text-gray-400">
                          {message.timestamp}s
                        </span>
                      )}
                    </div>
                    <p className="text-sm">{message.content}</p>
                  </div>
                </div>
              ))}

              {(!call.transcript || call.transcript.length === 0) && (
                <p className="text-gray-400 text-center py-8">
                  No transcript available
                </p>
              )}
            </div>
          </div>

          {/* Analysis Panel */}
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Summary</h2>
              <p className="text-gray-600 text-sm">
                {analytics?.call_summary || 'No summary available'}
              </p>
            </div>

            {/* Customer Intent */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                Customer Intent
              </h2>
              <p className="text-gray-600 text-sm">
                {analytics?.customer_intent || 'Not identified'}
              </p>
            </div>

            {/* Key Topics */}
            {analytics?.key_topics && analytics.key_topics.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">
                  Key Topics
                </h2>
                <div className="flex flex-wrap gap-2">
                  {analytics.key_topics.map((topic, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Improvement Suggestions */}
            {analytics?.improvement_suggestions &&
              analytics.improvement_suggestions.length > 0 && (
                <div className="bg-yellow-50 rounded-xl shadow-sm p-6">
                  <h2 className="text-lg font-semibold text-yellow-800 mb-3 flex items-center">
                    <Lightbulb className="w-5 h-5 mr-2" />
                    Improvement Suggestions
                  </h2>
                  <ul className="space-y-2">
                    {analytics.improvement_suggestions.map((suggestion, i) => (
                      <li key={i} className="text-sm text-yellow-700 flex items-start">
                        <span className="mr-2">•</span>
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {/* Action Items */}
            {analytics?.action_items && analytics.action_items.length > 0 && (
              <div className="bg-blue-50 rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold text-blue-800 mb-3">
                  Action Items
                </h2>
                <ul className="space-y-2">
                  {analytics.action_items.map((item, i) => (
                    <li
                      key={i}
                      className="text-sm text-blue-700 flex items-start"
                    >
                      <CheckCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Agent Performance */}
            {analytics?.agent_performance_score !== undefined && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">
                  Agent Performance
                </h2>
                <div className="flex items-center">
                  <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        analytics.agent_performance_score >= 80
                          ? 'bg-green-500'
                          : analytics.agent_performance_score >= 60
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{
                        width: `${analytics.agent_performance_score}%`,
                      }}
                    />
                  </div>
                  <span className="ml-3 font-semibold text-gray-700">
                    {analytics.agent_performance_score.toFixed(0)}/100
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## 6. Helper Components

### SentimentBadge (`components/voice/SentimentBadge.tsx`)

```tsx
import { Smile, Meh, Frown, HelpCircle } from 'lucide-react';

interface SentimentBadgeProps {
  sentiment?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function SentimentBadge({ sentiment, size = 'md' }: SentimentBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const iconSize = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const config = {
    positive: {
      bg: 'bg-green-100',
      text: 'text-green-700',
      icon: <Smile className={iconSize[size]} />,
      label: 'Positive',
    },
    neutral: {
      bg: 'bg-gray-100',
      text: 'text-gray-700',
      icon: <Meh className={iconSize[size]} />,
      label: 'Neutral',
    },
    negative: {
      bg: 'bg-red-100',
      text: 'text-red-700',
      icon: <Frown className={iconSize[size]} />,
      label: 'Negative',
    },
    mixed: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-700',
      icon: <HelpCircle className={iconSize[size]} />,
      label: 'Mixed',
    },
  };

  const cfg = config[sentiment as keyof typeof config] || config.neutral;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full ${cfg.bg} ${cfg.text} ${sizeClasses[size]}`}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  );
}
```

### StatsCard (`components/voice/StatsCard.tsx`)

```tsx
interface StatsCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  color?: 'blue' | 'green' | 'purple' | 'red' | 'gray';
}

export function StatsCard({
  title,
  value,
  icon,
  subtitle,
  color = 'blue',
}: StatsCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    red: 'bg-red-50 text-red-600',
    gray: 'bg-gray-50 text-gray-600',
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}
```

## 7. Install VAPI SDK

Add to `frontend/package.json`:

```json
{
  "dependencies": {
    "@vapi-ai/web": "^2.0.0"
  }
}
```

Then run:
```bash
npm install @vapi-ai/web
```

## 8. Environment Variables

Add to `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_VAPI_PUBLIC_KEY=your_vapi_public_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_assistant_id
```

## Navigation Update

Add dashboard link to your main navigation (e.g., in layout or header):

```tsx
<Link href="/dashboard">
  <BarChart className="w-5 h-5" />
  Analytics
</Link>
```

## Summary

The frontend implementation includes:

| Component | Purpose |
|-----------|---------|
| `/dashboard` | Main analytics overview |
| `/dashboard/calls/[id]` | Individual call details |
| `VoiceWidget` | Click-to-call button |
| `useVapi` hook | VAPI SDK integration |
| API client | Backend communication |

## Next Steps

After implementing:
1. Test the full flow end-to-end
2. Deploy to production
3. Configure VAPI with production webhook URL
