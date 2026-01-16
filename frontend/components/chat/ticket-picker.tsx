'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Search, Ticket, Loader2, CheckCircle, Circle, Clock } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

interface TicketResult {
  id: string
  ticket_number: number
  title: string
  description: string | null
  status: string
  priority: string
  category: string | null
  created_at: string
  source: string
}

interface TicketPickerProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (ticket: TicketResult) => void
  excludeIds: string[]
  token: string
}

const priorityColors = {
  low: 'bg-gray-500/20 text-gray-400',
  medium: 'bg-blue-500/20 text-blue-400',
  high: 'bg-orange-500/20 text-orange-400',
  critical: 'bg-red-500/20 text-red-400',
}

const statusIcons = {
  open: <Circle className="w-3.5 h-3.5 text-yellow-400" />,
  in_progress: <Clock className="w-3.5 h-3.5 text-blue-400" />,
  resolved: <CheckCircle className="w-3.5 h-3.5 text-green-400" />,
  closed: <CheckCircle className="w-3.5 h-3.5 text-gray-400" />,
}

export function TicketPicker({
  isOpen,
  onClose,
  onSelect,
  excludeIds,
  token,
}: TicketPickerProps) {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [tickets, setTickets] = useState<TicketResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const loadingRef = useRef(false)

  // Memoize excludeIds to avoid unnecessary re-renders
  const excludeIdsKey = useMemo(() => excludeIds.join(','), [excludeIds])

  // Load tickets effect - handles both initial load and search
  useEffect(() => {
    if (!isOpen || !token) return

    // Prevent concurrent loads
    if (loadingRef.current) return

    const loadTickets = async () => {
      loadingRef.current = true
      setIsLoading(true)
      setError(null)

      try {
        let result
        if (query.trim()) {
          result = await api.searchTicketsForChat(
            token,
            query,
            statusFilter !== 'all' ? statusFilter : undefined,
            15
          )
        } else {
          result = await api.getRecentTickets(
            token,
            statusFilter !== 'all' ? statusFilter : undefined,
            15
          )
        }
        // Filter out already attached tickets
        const filtered = result.tickets.filter(t => !excludeIds.includes(t.id))
        setTickets(filtered)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tickets')
        setTickets([])
      } finally {
        setIsLoading(false)
        loadingRef.current = false
      }
    }

    // Debounce the search
    const timer = setTimeout(loadTickets, 300)
    return () => clearTimeout(timer)
  }, [isOpen, query, statusFilter, token, excludeIdsKey])

  // Clear state when closing
  useEffect(() => {
    if (!isOpen) {
      setQuery('')
      setTickets([])
      setError(null)
    }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Slide-out panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-bg-primary border-l border-border-primary z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border-primary">
              <div className="flex items-center gap-2">
                <Ticket className="w-5 h-5 text-accent-primary" />
                <h2 className="font-semibold text-text-primary">Attach Ticket</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-bg-secondary transition-colors"
              >
                <X className="w-5 h-5 text-text-muted" />
              </button>
            </div>

            {/* Search */}
            <div className="p-4 space-y-3 border-b border-border-primary">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search tickets by title or description..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-bg-tertiary border border-border-primary text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary text-sm"
                  autoFocus
                />
              </div>

              {/* Status filter */}
              <div className="flex gap-2">
                {['all', 'open', 'in_progress', 'resolved'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      statusFilter === status
                        ? 'bg-accent-primary text-white'
                        : 'bg-bg-tertiary text-text-muted hover:text-text-primary'
                    )}
                  >
                    {status === 'all' ? 'All' : status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </button>
                ))}
              </div>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-4">
              {isLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
                </div>
              )}

              {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                  {error}
                </div>
              )}

              {!isLoading && !error && tickets.length === 0 && (
                <div className="text-center py-8">
                  <Ticket className="w-10 h-10 text-text-muted mx-auto mb-3" />
                  <p className="text-text-muted text-sm">
                    {query ? 'No tickets found' : 'No tickets yet'}
                  </p>
                  <p className="text-text-muted text-xs mt-1">
                    {query ? 'Try a different search term' : 'Create tickets from calls or chat'}
                  </p>
                </div>
              )}

              {tickets.length > 0 && (
                <div className="space-y-2">
                  {tickets.map((ticket) => (
                    <button
                      key={ticket.id}
                      onClick={() => {
                        onSelect(ticket)
                        onClose()
                      }}
                      className="w-full p-3 rounded-lg bg-bg-secondary border border-border-primary hover:border-accent-primary/50 hover:bg-bg-tertiary transition-all text-left"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-accent-primary text-sm">
                              #{ticket.ticket_number}
                            </span>
                            {statusIcons[ticket.status as keyof typeof statusIcons]}
                            <span
                              className={cn(
                                'px-1.5 py-0.5 rounded text-[10px] font-medium',
                                priorityColors[ticket.priority as keyof typeof priorityColors]
                              )}
                            >
                              {ticket.priority}
                            </span>
                            <span className="text-[10px] text-text-muted">
                              {ticket.source === 'chat' ? 'Chat' : 'Call'}
                            </span>
                          </div>
                          <p className="text-sm text-text-primary truncate">{ticket.title}</p>
                          {ticket.description && (
                            <p className="text-xs text-text-muted truncate mt-0.5">
                              {ticket.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
