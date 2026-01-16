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
        source_type: string
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
  async chat(token: string, message: string, conversationId?: string, attachedTicketIds?: string[]) {
    return this.request<{
      response: string
      conversation_id: string
      sources: Array<{ title: string; chunk: string }>
      tool_calls?: Array<{ name: string; result: Record<string, unknown> }>
      created_tickets?: Array<{
        id: string
        ticket_number: number
        title: string
        status: string
        priority: string
      }>
      referenced_tickets?: Array<{
        id: string
        ticket_number: number
        title: string
        status: string
        priority: string
      }>
    }>('/chat', {
      method: 'POST',
      token,
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        attached_ticket_ids: attachedTicketIds,
      }),
    })
  }

  // Chat conversations
  async listConversations(token: string) {
    return this.request<{
      conversations: Array<{
        id: string
        title: string
        created_at: string
        updated_at: string
        attached_ticket_ids: string[]
      }>
    }>('/chat/conversations', { token })
  }

  async getConversation(token: string, conversationId: string) {
    return this.request<{
      id: string
      title: string
      messages: Array<{
        role: string
        content: string
        timestamp: string
        sources?: Array<{ title: string; chunk: string }>
        tool_calls?: Array<{ name: string; result: Record<string, unknown> }>
      }>
      attached_ticket_ids: string[]
      created_at: string
      updated_at: string
    }>(`/chat/conversations/${conversationId}`, { token })
  }

  async deleteConversation(token: string, conversationId: string) {
    return this.request<{ success: boolean }>(`/chat/conversations/${conversationId}`, {
      method: 'DELETE',
      token,
    })
  }

  async updateConversationTickets(token: string, conversationId: string, ticketIds: string[]) {
    return this.request<{ success: boolean; attached_ticket_ids: string[] }>(
      `/chat/conversations/${conversationId}/tickets`,
      {
        method: 'PATCH',
        token,
        body: JSON.stringify(ticketIds),
      }
    )
  }

  async generateConversationTitle(token: string, conversationId: string) {
    return this.request<{ title: string; generated: boolean }>(
      `/chat/conversations/${conversationId}/generate-title`,
      {
        method: 'POST',
        token,
      }
    )
  }

  // Get recent tickets for chat picker (no search query required)
  async getRecentTickets(token: string, status?: string, limit?: number) {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (limit) params.set('limit', limit.toString())

    const queryString = params.toString()
    return this.request<{
      tickets: Array<{
        id: string
        ticket_number: number
        title: string
        description: string | null
        status: string
        priority: string
        category: string | null
        created_at: string
        updated_at: string
        user_id: string | null
        source: string
      }>
      count: number
    }>(`/chat/tickets/recent${queryString ? `?${queryString}` : ''}`, { token })
  }

  // Ticket search for chat picker
  async searchTicketsForChat(token: string, query: string, status?: string, limit?: number) {
    const params = new URLSearchParams({ q: query })
    if (status) params.set('status', status)
    if (limit) params.set('limit', limit.toString())

    return this.request<{
      tickets: Array<{
        id: string
        ticket_number: number
        title: string
        description: string | null
        status: string
        priority: string
        category: string | null
        created_at: string
        updated_at: string
        user_id: string | null
        source: string
      }>
      count: number
    }>(`/chat/tickets/search?${params}`, { token })
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

  async getAnalyticsDashboard(token: string, days: number = 7) {
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
    }>(`/analytics/dashboard?days=${days}`, { token })
  }

  async getVoiceCalls(token: string, params?: {
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
    }>(`/voice/calls?${query}`, { token })
  }

  async getCallDetail(token: string, callId: string) {
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
    }>(`/voice/calls/${callId}`, { token })
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

  async getCumulativeDashboard(token: string) {
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
        top_pain_points: Array<{ text: string; count: number }>
        top_feature_requests: Array<{ text: string; count: number }>
        top_complaints: Array<{ text: string; count: number }>
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
    }>('/analytics/cumulative', { token })
  }

  // ========================================
  // ENHANCED ANALYTICS ENDPOINTS
  // ========================================

  async getCustomers(token: string, params?: {
    page?: number
    pageSize?: number
    riskLevel?: string
    customerType?: string
  }) {
    const query = new URLSearchParams()
    if (params?.page) query.set('page', params.page.toString())
    if (params?.pageSize) query.set('page_size', params.pageSize.toString())
    if (params?.riskLevel) query.set('risk_level', params.riskLevel)
    if (params?.customerType) query.set('customer_type', params.customerType)

    return this.request<{
      customers: Array<{
        id: string
        name: string | null
        email: string | null
        phone: string | null
        customer_type: string
        total_calls: number
        avg_satisfaction: number
        churn_risk_level: string
        churn_risk_score: number
        last_call_at: string | null
      }>
      total: number
      page: number
      page_size: number
    }>(`/analytics/customers?${query}`, { token })
  }

  async getHighRiskCustomers(token: string, limit: number = 10) {
    return this.request<Array<{
      id: string
      name: string | null
      email: string | null
      phone: string | null
      churn_risk_score: number
      churn_risk_factors: string[]
      recommended_actions: string[]
      last_call_at: string | null
      total_calls: number
    }>>(`/analytics/high-risk-customers?limit=${limit}`, { token })
  }

  async getFeedback(token: string, feedbackType?: string, limit: number = 20) {
    const query = new URLSearchParams()
    if (feedbackType) query.set('feedback_type', feedbackType)
    query.set('limit', limit.toString())

    return this.request<Array<{
      text: string
      count: number
      category: string | null
      first_mentioned: string | null
      last_mentioned: string | null
    }>>(`/analytics/feedback?${query}`, { token })
  }

  async getActionItems(token: string, limit: number = 20) {
    return this.request<Array<{
      call_id: string
      call_date: string
      customer_name: string | null
      action_items: string[]
      commitments_made: string[]
      follow_up_deadline: string | null
    }>>(`/analytics/action-items?limit=${limit}`, { token })
  }

  async getKnowledgeGaps(token: string, limit: number = 10) {
    return this.request<Array<{
      text: string
      count: number
      category: string | null
      first_mentioned: string | null
      last_mentioned: string | null
    }>>(`/analytics/knowledge-gaps?limit=${limit}`, { token })
  }

  async getAgentPerformanceSummary(token: string, days: number = 30) {
    return this.request<{
      total_calls_analyzed: number
      average_scores: {
        overall: number
        empathy: number
        knowledge: number
        communication: number
        efficiency: number
        opening: number
        closing: number
      }
      top_strengths: Array<{ text: string; count: number }>
      top_areas_for_improvement: Array<{ text: string; count: number }>
      top_training_recommendations: Array<{ text: string; count: number }>
    }>(`/analytics/agent-performance-summary?days=${days}`, { token })
  }

  // ========================================
  // GRANULAR ANALYTICS ENDPOINTS
  // ========================================

  async getTimeBasedAnalytics(token: string, days: number = 30) {
    return this.request<{
      hourly_distribution: Record<number, { calls: number; avg_sentiment: number }>
      day_of_week_distribution: Record<string, { calls: number; avg_duration: number }>
      peak_hours: Array<{ hour: number; calls: number }>
      total_calls: number
      days_analyzed: number
    }>(`/analytics/time-based?days=${days}`, { token })
  }

  async getEffortScoreAnalytics(token: string, days: number = 30) {
    return this.request<{
      ces_distribution: Record<number, number>
      average_ces: number
      repeat_rate_percent: number
      average_transfers: number
      total_calls_with_repeats: number
      ces_trend: Array<{ date: string; avg_ces: number; calls: number }>
      total_calls: number
      ces_breakdown: {
        effortless: number
        moderate: number
        high_effort: number
      }
    }>(`/analytics/effort-scores?days=${days}`, { token })
  }

  async getEscalationAnalytics(token: string, days: number = 30) {
    return this.request<{
      total_calls: number
      escalated_calls: number
      escalation_rate_percent: number
      escalation_resolution_rate_percent: number
      escalation_levels: Record<string, number>
      top_escalation_reasons: Array<{ reason: string; count: number }>
      top_departments: Array<{ department: string; count: number }>
      categories_leading_to_escalation: Array<{ category: string; count: number }>
    }>(`/analytics/escalation-analytics?days=${days}`, { token })
  }

  async getCompetitiveIntelligence(token: string, days: number = 30) {
    return this.request<{
      total_calls: number
      calls_with_competitor_mentions: number
      competitor_mention_rate_percent: number
      switching_intent_rate_percent: number
      switching_intent_count: number
      top_competitors: Array<{ name: string; mentions: number }>
      top_comparison_requests: Array<{ comparison: string; count: number }>
      price_sensitivity_distribution: Record<string, number>
    }>(`/analytics/competitive-intelligence?days=${days}`, { token })
  }

  async getProductAnalytics(token: string, days: number = 30) {
    return this.request<{
      total_calls: number
      upsell_opportunities: number
      upsell_opportunity_rate_percent: number
      top_products_discussed: Array<{ product: string; mentions: number }>
      top_features_requested: Array<{ feature: string; requests: number }>
      top_problematic_features: Array<{ feature: string; issues: number }>
      top_cross_sell_suggestions: Array<{ suggestion: string; count: number }>
    }>(`/analytics/product-analytics?days=${days}`, { token })
  }

  async getConversationQualityAnalytics(token: string, days: number = 30) {
    return this.request<{
      total_calls: number
      average_clarity_score: number
      average_empathy_phrases: number
      average_jargon_usage: number
      average_response_time_seconds: number
      average_agent_wpm: number
      average_customer_wpm: number
      average_agent_talk_percentage: number
      average_hold_time_seconds: number
      calls_with_high_clarity: number
      calls_with_low_clarity: number
    }>(`/analytics/conversation-quality?days=${days}`, { token })
  }

  // ========================================
  // TICKETS API
  // ========================================

  async getTickets(token: string, params?: {
    page?: number
    pageSize?: number
    status?: string
    priority?: string
    category?: string
  }) {
    const query = new URLSearchParams()
    if (params?.page) query.set('page', params.page.toString())
    if (params?.pageSize) query.set('page_size', params.pageSize.toString())
    if (params?.status) query.set('status', params.status)
    if (params?.priority) query.set('priority', params.priority)
    if (params?.category) query.set('category', params.category)

    return this.request<{
      tickets: Array<{
        id: string
        title: string
        description: string | null
        status: string
        priority: string
        category: string | null
        call_id: string | null
        user_id: string | null
        customer_name: string | null
        customer_email: string | null
        customer_phone: string | null
        created_at: string
        updated_at: string
        resolved_at: string | null
      }>
      total: number
      page: number
      page_size: number
    }>(`/tickets?${query}`, { token })
  }

  async getTicketStats(token: string) {
    return this.request<{
      total: number
      open: number
      in_progress: number
      resolved: number
      closed: number
      by_priority: {
        low: number
        medium: number
        high: number
        critical: number
      }
      by_category: Record<string, number>
      avg_resolution_time_hours: number | null
      tickets_today: number
      tickets_this_week: number
    }>('/tickets/stats', { token })
  }

  async getTicketDetail(token: string, ticketId: string) {
    return this.request<{
      id: string
      title: string
      description: string | null
      status: string
      priority: string
      category: string | null
      call_id: string | null
      user_id: string | null
      customer_name: string | null
      customer_email: string | null
      customer_phone: string | null
      created_at: string
      updated_at: string
      resolved_at: string | null
      action_items: string[] | null
      call?: {
        id: string
        vapi_call_id: string
        started_at: string
        duration_seconds: number | null
        sentiment: string | null
      }
    }>(`/tickets/${ticketId}`, { token })
  }

  async updateTicket(token: string, ticketId: string, updates: {
    status?: string
    priority?: string
    title?: string
    description?: string
  }) {
    return this.request<{
      id: string
      title: string
      status: string
      priority: string
      updated_at: string
    }>(`/tickets/${ticketId}`, {
      method: 'PATCH',
      token,
      body: JSON.stringify(updates),
    })
  }
}

export const api = new ApiClient(API_BASE_URL)
