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
    >('/users')
  }
}

export const api = new ApiClient(API_BASE_URL)
