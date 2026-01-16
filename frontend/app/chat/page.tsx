'use client'

import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Bot,
  User,
  Sparkles,
  FileText,
  Loader2,
  Plus,
  Ticket,
  PanelLeftClose,
  PanelLeft,
  Command,
} from 'lucide-react'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { TicketPicker } from '@/components/chat/ticket-picker'
import { TicketChip } from '@/components/chat/ticket-chip'
import { TicketCardInline } from '@/components/chat/ticket-card-inline'
import { ChatHistorySidebar } from '@/components/chat/chat-history-sidebar'

interface AttachedTicket {
  id: string
  ticket_number: number
  title: string
  status: string
  priority: string
}

interface TicketInfo {
  id: string
  ticket_number: number
  title: string
  status: string
  priority: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ title: string; chunk: string }>
  created_tickets?: TicketInfo[]
  referenced_tickets?: TicketInfo[]
}

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  attached_ticket_ids: string[]
}

function ChatPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { token } = useOnboardingStore()

  // Chat state
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [showSources, setShowSources] = useState<number | null>(null)
  const [attachedTickets, setAttachedTickets] = useState<AttachedTicket[]>([])
  const [isTicketPickerOpen, setIsTicketPickerOpen] = useState(false)

  // Sidebar state
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoadingConversations, setIsLoadingConversations] = useState(true)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Load conversations on mount
  useEffect(() => {
    if (!token) return

    const loadConversations = async () => {
      try {
        const result = await api.listConversations(token)
        setConversations(result.conversations || [])
      } catch (error) {
        console.error('Failed to load conversations:', error)
      } finally {
        setIsLoadingConversations(false)
      }
    }

    loadConversations()
  }, [token])

  // Handle URL parameter for auto-attaching tickets
  useEffect(() => {
    const attachParam = searchParams.get('attach')
    if (attachParam && token) {
      const ticketIds = attachParam.split(',')
      // Load ticket details for the IDs
      const loadTickets = async () => {
        try {
          // Search for each ticket by ID - in a real app you'd have a batch endpoint
          const tickets: AttachedTicket[] = []
          for (const id of ticketIds) {
            const result = await api.searchTicketsForChat(token, id, undefined, 1)
            if (result.tickets.length > 0) {
              const t = result.tickets[0]
              tickets.push({
                id: t.id,
                ticket_number: t.ticket_number,
                title: t.title,
                status: t.status,
                priority: t.priority,
              })
            }
          }
          setAttachedTickets(tickets)
        } catch (error) {
          console.error('Failed to load attached tickets:', error)
        }
      }
      loadTickets()
    }
  }, [searchParams, token])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K - Focus search / new chat
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        handleNewChat()
        inputRef.current?.focus()
      }
      // Cmd/Ctrl + Shift + T - Open ticket picker
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 't') {
        e.preventDefault()
        setIsTicketPickerOpen(true)
      }
      // Escape - Close ticket picker
      if (e.key === 'Escape') {
        setIsTicketPickerOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleAttachTicket = (ticket: AttachedTicket) => {
    if (!attachedTickets.find((t) => t.id === ticket.id)) {
      setAttachedTickets((prev) => [...prev, ticket])
    }
  }

  const handleRemoveTicket = (ticketId: string) => {
    setAttachedTickets((prev) => prev.filter((t) => t.id !== ticketId))
  }

  const handleNewChat = () => {
    setMessages([])
    setConversationId(null)
    setAttachedTickets([])
    setShowSources(null)
  }

  const handleSelectConversation = async (id: string) => {
    if (!token || id === conversationId) return

    try {
      setIsLoading(true)
      const conv = await api.getConversation(token, id)

      setConversationId(id)
      setMessages(
        conv.messages.map((m) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          sources: m.sources,
        }))
      )

      // Load attached tickets if any
      if (conv.attached_ticket_ids && conv.attached_ticket_ids.length > 0) {
        const tickets: AttachedTicket[] = []
        for (const ticketId of conv.attached_ticket_ids.slice(0, 5)) {
          const result = await api.searchTicketsForChat(token, ticketId, undefined, 1)
          if (result.tickets.length > 0) {
            const t = result.tickets[0]
            tickets.push({
              id: t.id,
              ticket_number: t.ticket_number,
              title: t.title,
              status: t.status,
              priority: t.priority,
            })
          }
        }
        setAttachedTickets(tickets)
      } else {
        setAttachedTickets([])
      }
    } catch (error) {
      console.error('Failed to load conversation:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteConversation = async (id: string) => {
    if (!token) return

    try {
      await api.deleteConversation(token, id)
      setConversations((prev) => prev.filter((c) => c.id !== id))

      // If deleting active conversation, start new chat
      if (id === conversationId) {
        handleNewChat()
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !token) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const attachedTicketIds = attachedTickets.map((t) => t.id)
      const response = await api.chat(
        token,
        userMessage,
        conversationId || undefined,
        attachedTicketIds.length > 0 ? attachedTicketIds : undefined
      )

      const isNewConversation = !conversationId
      setConversationId(response.conversation_id)

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.response,
          sources: response.sources,
          created_tickets: response.created_tickets,
          referenced_tickets: response.referenced_tickets,
        },
      ])

      // Update conversations list
      if (isNewConversation) {
        // Add new conversation to list with temporary title
        const newConv: Conversation = {
          id: response.conversation_id,
          title: userMessage.slice(0, 50) + (userMessage.length > 50 ? '...' : ''),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          attached_ticket_ids: attachedTicketIds,
        }
        setConversations((prev) => [newConv, ...prev])

        // Generate AI title in background
        api.generateConversationTitle(token, response.conversation_id)
          .then((result) => {
            if (result.title) {
              setConversations((prev) =>
                prev.map((c) =>
                  c.id === response.conversation_id
                    ? { ...c, title: result.title }
                    : c
                )
              )
            }
          })
          .catch((err) => console.error('Failed to generate title:', err))
      } else {
        // Update existing conversation's updated_at
        setConversations((prev) =>
          prev.map((c) =>
            c.id === response.conversation_id
              ? { ...c, updated_at: new Date().toISOString() }
              : c
          )
        )
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthenticatedLayout>
      <div className="h-screen flex overflow-hidden bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary">
        {/* Sidebar */}
        <AnimatePresence>
          {isSidebarOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 256, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex-shrink-0 overflow-hidden"
            >
              <ChatHistorySidebar
                conversations={conversations}
                activeConversationId={conversationId}
                isLoading={isLoadingConversations}
                onSelectConversation={handleSelectConversation}
                onNewChat={handleNewChat}
                onDeleteConversation={handleDeleteConversation}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <header className="border-b border-border-primary bg-bg-secondary/50 backdrop-blur-sm flex-shrink-0">
            <div className="px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors text-text-muted hover:text-text-primary"
                    title={isSidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
                  >
                    {isSidebarOpen ? (
                      <PanelLeftClose className="w-5 h-5" />
                    ) : (
                      <PanelLeft className="w-5 h-5" />
                    )}
                  </button>
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h1 className="font-semibold text-text-primary text-sm">SupportIQ Chat</h1>
                    <p className="text-[10px] text-text-muted">AI assistant with ticket management</p>
                  </div>
                </div>

                {/* Keyboard Shortcuts Hint */}
                <div className="hidden md:flex items-center gap-3 text-[10px] text-text-muted">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 rounded bg-bg-tertiary border border-border-primary">
                      <Command className="w-3 h-3 inline" />K
                    </kbd>
                    <span>New</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 rounded bg-bg-tertiary border border-border-primary">
                      <Command className="w-3 h-3 inline" />⇧T
                    </kbd>
                    <span>Attach</span>
                  </span>
                </div>
              </div>

              {/* Attached Tickets Bar */}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <button
                  onClick={() => setIsTicketPickerOpen(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-dashed border-border-primary text-text-muted hover:border-accent-primary hover:text-accent-primary transition-colors text-xs"
                >
                  <Plus className="w-3 h-3" />
                  <Ticket className="w-3 h-3" />
                  <span>Attach</span>
                </button>

                {attachedTickets.map((ticket) => (
                  <TicketChip
                    key={ticket.id}
                    ticketNumber={ticket.ticket_number}
                    title={ticket.title}
                    status={ticket.status}
                    priority={ticket.priority}
                    onRemove={() => handleRemoveTicket(ticket.id)}
                  />
                ))}

                {attachedTickets.length > 0 && (
                  <span className="text-[10px] text-text-muted ml-1">
                    {attachedTickets.length} ticket{attachedTickets.length > 1 ? 's' : ''} for context
                  </span>
                )}
              </div>
            </div>
          </header>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-16"
                >
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-primary/20 to-purple-600/20 flex items-center justify-center mx-auto mb-5">
                    <Bot className="w-8 h-8 text-accent-primary" />
                  </div>
                  <h2 className="text-xl font-semibold text-text-primary mb-2">
                    How can I help you today?
                  </h2>
                  <p className="text-text-muted text-sm max-w-md mx-auto">
                    Ask questions, create tickets, or manage existing ones. I have access to your
                    knowledge base and ticket system.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 mt-5">
                    {[
                      'Create a ticket for a billing issue',
                      "What's the status of ticket #1?",
                      'Search for open tickets',
                    ].map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => setInput(suggestion)}
                        className="px-3 py-1.5 rounded-full bg-bg-tertiary text-text-secondary text-xs hover:bg-accent-primary/10 hover:text-accent-primary transition-colors"
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
                    className={`flex gap-3 ${
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {message.role === 'assistant' && (
                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}

                    <div className={`max-w-[80%] ${message.role === 'user' ? 'order-1' : ''}`}>
                      <div
                        className={`rounded-2xl px-4 py-2.5 ${
                          message.role === 'user'
                            ? 'bg-accent-primary text-white rounded-br-md'
                            : 'bg-bg-tertiary text-text-primary rounded-bl-md'
                        }`}
                      >
                        <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                      </div>

                      {/* Created Tickets */}
                      {message.created_tickets && message.created_tickets.length > 0 && (
                        <div className="mt-2 space-y-2">
                          {message.created_tickets.map((ticket) => (
                            <TicketCardInline
                              key={ticket.id}
                              id={ticket.id}
                              ticketNumber={ticket.ticket_number}
                              title={ticket.title}
                              status={ticket.status}
                              priority={ticket.priority}
                              isCreated={true}
                            />
                          ))}
                        </div>
                      )}

                      {/* Referenced Tickets */}
                      {message.referenced_tickets && message.referenced_tickets.length > 0 && (
                        <div className="mt-2 space-y-2">
                          {message.referenced_tickets.map((ticket) => (
                            <TicketCardInline
                              key={ticket.id}
                              id={ticket.id}
                              ticketNumber={ticket.ticket_number}
                              title={ticket.title}
                              status={ticket.status}
                              priority={ticket.priority}
                            />
                          ))}
                        </div>
                      )}

                      {message.sources && message.sources.length > 0 && (
                        <div className="mt-2">
                          <button
                            onClick={() => setShowSources(showSources === index ? null : index)}
                            className="flex items-center gap-1 text-[10px] text-text-muted hover:text-accent-primary transition-colors"
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
                                    className="p-2.5 rounded-lg bg-bg-secondary border border-border-primary text-[10px]"
                                  >
                                    <p className="font-medium text-text-primary mb-0.5">
                                      {source.title}
                                    </p>
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
                      <div className="w-7 h-7 rounded-lg bg-bg-tertiary flex items-center justify-center flex-shrink-0 order-2">
                        <User className="w-3.5 h-3.5 text-text-secondary" />
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {isLoading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-primary to-purple-600 flex items-center justify-center">
                    <Bot className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="bg-bg-tertiary rounded-2xl rounded-bl-md px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-accent-primary" />
                      <span className="text-text-muted text-sm">Thinking...</span>
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-border-primary bg-bg-secondary/50 backdrop-blur-sm flex-shrink-0">
            <form onSubmit={handleSubmit} className="max-w-3xl mx-auto px-4 py-3">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question or create a ticket..."
                  className="flex-1 px-4 py-2.5 rounded-xl bg-bg-tertiary border border-border-primary text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary transition-all text-sm"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="px-4 py-2.5 rounded-xl bg-accent-primary text-white font-medium hover:bg-accent-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Ticket Picker Modal */}
        {token && (
          <TicketPicker
            isOpen={isTicketPickerOpen}
            onClose={() => setIsTicketPickerOpen(false)}
            onSelect={handleAttachTicket}
            excludeIds={attachedTickets.map((t) => t.id)}
            token={token}
          />
        )}
      </div>
    </AuthenticatedLayout>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <AuthenticatedLayout>
        <div className="h-screen flex items-center justify-center bg-bg-primary">
          <Loader2 className="w-8 h-8 animate-spin text-accent-primary" />
        </div>
      </AuthenticatedLayout>
    }>
      <ChatPageContent />
    </Suspense>
  )
}
