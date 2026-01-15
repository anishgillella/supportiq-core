'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles, FileText, Loader2, Database } from 'lucide-react'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ title: string; chunk: string }>
}

export default function ChatPage() {
  const router = useRouter()
  const { token } = useOnboardingStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [showSources, setShowSources] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !token) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await api.chat(token, userMessage, conversationId || undefined)
      setConversationId(response.conversation_id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.response,
        sources: response.sources
      }])
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthenticatedLayout>
    <div className="min-h-screen bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary flex flex-col">
      {/* Header */}
      <header className="border-b border-border-primary bg-bg-secondary/50 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-text-primary">SupportIQ Chat</h1>
              <p className="text-xs text-text-muted">AI-powered support assistant</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push('/knowledge')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border-primary text-text-secondary hover:bg-bg-tertiary transition-colors text-sm"
            >
              <Database className="w-4 h-4" />
              Knowledge Base
            </button>
            <button
              onClick={() => {
                setMessages([])
                setConversationId(null)
              }}
              className="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors"
            >
              New Chat
            </button>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-20"
            >
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent-primary/20 to-purple-600/20 flex items-center justify-center mx-auto mb-6">
                <Bot className="w-10 h-10 text-accent-primary" />
              </div>
              <h2 className="text-2xl font-semibold text-text-primary mb-2">
                How can I help you today?
              </h2>
              <p className="text-text-muted max-w-md mx-auto">
                Ask me anything about your products, services, or company. I'll use your knowledge base to provide accurate answers.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-6">
                {[
                  "What products do you offer?",
                  "How does pricing work?",
                  "What are your support hours?"
                ].map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(suggestion)}
                    className="px-4 py-2 rounded-full bg-bg-tertiary text-text-secondary text-sm hover:bg-accent-primary/10 hover:text-accent-primary transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          <AnimatePresence>
            {messages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={`max-w-[80%] ${message.role === 'user' ? 'order-1' : ''}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-accent-primary text-white rounded-br-md'
                        : 'bg-bg-tertiary text-text-primary rounded-bl-md'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>

                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-2">
                      <button
                        onClick={() => setShowSources(showSources === index ? null : index)}
                        className="flex items-center gap-1 text-xs text-text-muted hover:text-accent-primary transition-colors"
                      >
                        <FileText className="w-3 h-3" />
                        {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
                      </button>

                      <AnimatePresence>
                        {showSources === index && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-2 space-y-2"
                          >
                            {message.sources.map((source, i) => (
                              <div
                                key={i}
                                className="p-3 rounded-lg bg-bg-secondary border border-border-primary text-xs"
                              >
                                <p className="font-medium text-text-primary mb-1">{source.title}</p>
                                <p className="text-text-muted">{source.chunk}</p>
                              </div>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )}
                </div>

                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-lg bg-bg-tertiary flex items-center justify-center flex-shrink-0 order-2">
                    <User className="w-4 h-4 text-text-secondary" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-4"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-bg-tertiary rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-accent-primary" />
                  <span className="text-text-muted">Thinking...</span>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-border-primary bg-bg-secondary/50 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 px-4 py-3 rounded-xl bg-bg-tertiary border border-border-primary text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary transition-all"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 rounded-xl bg-accent-primary text-white font-medium hover:bg-accent-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
        </form>
      </div>
    </div>
    </AuthenticatedLayout>
  )
}
