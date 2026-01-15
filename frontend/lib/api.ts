const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface ApiOptions extends RequestInit {
  token?: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
    const { token, ...fetchOptions } = options

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...fetchOptions,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'An error occurred' }))
      throw new Error(error.detail || 'An error occurred')
    }

    return response.json()
  }

  // Auth endpoints
  async register(email: string, password: string, companyName?: string, companyWebsite?: string) {
    return this.request<{ access_token: string; user_id: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        company_name: companyName,
        company_website: companyWebsite
      }),
    })
  }

  // Knowledge base endpoints
  async scrapeWebsite(token: string, websiteUrl: string) {
    return this.request<{ success: boolean; documents_count: number }>('/knowledge/scrape', {
      method: 'POST',
      token,
      body: JSON.stringify({ website_url: websiteUrl }),
    })
  }

  async uploadDocument(token: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${this.baseUrl}/knowledge/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(error.detail || 'Upload failed')
    }

    return response.json()
  }

  async getKnowledgeBase(token: string) {
    return this.request<{
      documents: Array<{
        id: string
        title: string
        source: string
        chunks_count: number
        created_at: string
      }>
    }>('/knowledge/documents', { token })
  }

  async deleteDocument(token: string, documentId: string) {
    return this.request<{ success: boolean }>(`/knowledge/documents/${documentId}`, {
      method: 'DELETE',
      token,
    })
  }

  // Chat endpoint
  async chat(token: string, message: string, conversationId?: string) {
    return this.request<{
      response: string
      conversation_id: string
      sources: Array<{ title: string; chunk: string }>
    }>('/chat', {
      method: 'POST',
      token,
      body: JSON.stringify({ message, conversation_id: conversationId }),
    })
  }

  async login(email: string, password: string) {
    return this.request<{ access_token: string; user_id: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async getCurrentUser(token: string) {
    return this.request<{ id: string; email: string; current_step: number }>('/auth/me', {
      token,
    })
  }

  async checkEmail(email: string) {
    return this.request<{ exists: boolean }>(`/auth/check-email?email=${encodeURIComponent(email)}`)
  }

  // Progress endpoints
  async getProgress(token: string) {
    return this.request<{
      current_step: number
      onboarding_completed: boolean
      profile: {
        about_me: string | null
        street_address: string | null
        city: string | null
        state: string | null
        zip_code: string | null
        birthdate: string | null
      } | null
    }>('/progress', { token })
  }

  async updateProgress(
    token: string,
    data: {
      step: number
      about_me?: string
      street_address?: string
      city?: string
      state?: string
      zip_code?: string
      birthdate?: string
    }
  ) {
    return this.request<{ success: boolean }>('/progress', {
      method: 'PUT',
      token,
      body: JSON.stringify(data),
    })
  }

  async completeOnboarding(token: string) {
    return this.request<{ success: boolean }>('/progress/complete', {
      method: 'POST',
      token,
    })
  }

  // Admin endpoints
  async getConfig() {
    return this.request<{
      page2: string[]
      page3: string[]
    }>('/admin/config')
  }

  async updateConfig(config: { page2: string[]; page3: string[] }) {
    return this.request<{ success: boolean }>('/admin/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  }

  // Data endpoint (public)
  async getAllUsers() {
    return this.request<
      Array<{
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
      }>
    >('/supportiq_users')
  }

  // ========================================
  // VOICE ANALYTICS API
  // ========================================

  async getAnalyticsDashboard(days: number = 7) {
    return this.request<{
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
    }>(`/analytics/dashboard?days=${days}`)
  }

  async getVoiceCalls(params?: {
    page?: number
    pageSize?: number
    status?: string
    sentiment?: string
  }) {
    const query = new URLSearchParams()
    if (params?.page) query.set('page', params.page.toString())
    if (params?.pageSize) query.set('page_size', params.pageSize.toString())
    if (params?.status) query.set('status', params.status)
    if (params?.sentiment) query.set('sentiment', params.sentiment)

    return this.request<{
      calls: Array<{
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
      }>
      total: number
      page: number
      page_size: number
    }>(`/voice/calls?${query}`)
  }

  async getCallDetail(callId: string) {
    return this.request<{
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
    }>(`/voice/calls/${callId}`)
  }

  // Voice call initiation
  async initiateCall(token: string, phoneNumber?: string, assistantId?: string) {
    return this.request<{
      success: boolean
      call_id: string | null
      web_call_url: string | null
      message: string
    }>('/voice/calls/initiate', {
      method: 'POST',
      token,
      body: JSON.stringify({
        phone_number: phoneNumber,
        assistant_id: assistantId,
      }),
    })
  }

  async getCumulativeDashboard() {
    return this.request<{
      overview: {
        total_calls: number
        total_duration_seconds: number
        avg_duration_seconds: number
        total_resolved: number
        total_escalated: number
        resolution_rate: number
        avg_sentiment_score: number
        avg_csat: number
        avg_agent_score: number
        calls_today: number
        calls_this_week: number
        calls_this_month: number
        calls_vs_last_week: number
        resolution_vs_last_week: number
        sentiment_vs_last_week: number
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
      customer_insights: {
        total_unique_customers: number
        repeat_caller_rate: number
        avg_calls_per_customer: number
        top_pain_points: Array<{ item: string; count: number }>
        top_feature_requests: Array<{ item: string; count: number }>
        top_complaints: Array<{ item: string; count: number }>
        high_risk_customers: number
        avg_churn_risk: number
      }
      agent_leaderboard: Array<{
        agent_type: string
        total_calls: number
        avg_score: number
        avg_resolution_rate: number
        avg_csat: number
      }>
      weekly_trends: Array<{
        date: string
        calls: number
        avg_sentiment: number
        resolution_rate: number
      }>
      monthly_trends: Array<{
        date: string
        calls: number
        avg_sentiment: number
        resolution_rate: number
      }>
      top_issues_all_time: Array<{ category: string; count: number }>
      recent_calls: Array<{
        id: string
        started_at: string
        duration: number | null
        status: string
        sentiment: string | null
      }>
    }>('/analytics/cumulative')
  }
}

export const api = new ApiClient(API_BASE_URL)
