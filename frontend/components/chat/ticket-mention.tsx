'use client'

import { useState, useEffect, useCallback, useRef, forwardRef, useImperativeHandle } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Ticket, Loader2, CheckCircle, Circle, Clock } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

interface TicketResult {
  id: string
  ticket_number: number
  title: string
  status: string
  priority: string
}

interface TicketMentionProps {
  isOpen: boolean
  query: string
  token: string
  excludeIds: string[]
  onSelect: (ticket: TicketResult) => void
  onClose: () => void
  position: { top: number; left: number }
  selectedIndex: number
  onTicketsLoaded?: (count: number, tickets: TicketResult[]) => void
}

export interface TicketMentionRef {
  selectCurrent: () => void
}

const priorityColors = {
  low: 'bg-gray-500/20 text-gray-400',
  medium: 'bg-blue-500/20 text-blue-400',
  high: 'bg-orange-500/20 text-orange-400',
  critical: 'bg-red-500/20 text-red-400',
}

const statusIcons = {
  open: <Circle className="w-3 h-3 text-yellow-400" />,
  in_progress: <Clock className="w-3 h-3 text-blue-400" />,
  resolved: <CheckCircle className="w-3 h-3 text-green-400" />,
  closed: <CheckCircle className="w-3 h-3 text-gray-400" />,
}

export const TicketMention = forwardRef<TicketMentionRef, TicketMentionProps>(
  function TicketMention(
    {
      isOpen,
      query,
      token,
      excludeIds,
      onSelect,
      onClose,
      position,
      selectedIndex,
      onTicketsLoaded,
    },
    ref
  ) {
    const [tickets, setTickets] = useState<TicketResult[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const listRef = useRef<HTMLDivElement>(null)
    const loadingRef = useRef(false)

    // Store callbacks in refs to avoid dependency issues
    const onTicketsLoadedRef = useRef(onTicketsLoaded)
    onTicketsLoadedRef.current = onTicketsLoaded

    // Expose selectCurrent method via ref
    useImperativeHandle(ref, () => ({
      selectCurrent: () => {
        if (tickets.length > 0 && selectedIndex >= 0 && selectedIndex < tickets.length) {
          onSelect(tickets[selectedIndex])
        }
      },
    }), [tickets, selectedIndex, onSelect])

    // Load tickets when opened or query changes
    useEffect(() => {
      if (!isOpen || !token) return

      // Prevent concurrent loads
      if (loadingRef.current) return

      const loadTickets = async () => {
        loadingRef.current = true
        setIsLoading(true)

        try {
          let result
          if (query.trim()) {
            result = await api.searchTicketsForChat(token, query, undefined, 8)
          } else {
            result = await api.getRecentTickets(token, undefined, 8)
          }

          const filtered = result.tickets
            .filter((t) => !excludeIds.includes(t.id))
            .map((t) => ({
              id: t.id,
              ticket_number: t.ticket_number,
              title: t.title,
              status: t.status,
              priority: t.priority,
            }))

          setTickets(filtered)
          onTicketsLoadedRef.current?.(filtered.length, filtered)
        } catch (err) {
          console.error('Failed to load tickets for mention:', err)
          setTickets([])
          onTicketsLoadedRef.current?.(0, [])
        } finally {
          setIsLoading(false)
          loadingRef.current = false
        }
      }

      const timer = setTimeout(loadTickets, 150)
      return () => clearTimeout(timer)
    }, [isOpen, query, token, excludeIds.join(',')])

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const item = listRef.current.children[selectedIndex] as HTMLElement
      if (item) {
        item.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex])

  // Clear when closed
  useEffect(() => {
    if (!isOpen) {
      setTickets([])
    }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ duration: 0.15 }}
          style={{
            position: 'absolute',
            bottom: position.top,
            left: position.left,
          }}
          className="w-72 max-h-64 bg-bg-primary border border-border-primary rounded-lg shadow-xl overflow-hidden z-50"
        >
          {/* Header */}
          <div className="px-3 py-2 border-b border-border-primary bg-bg-secondary/50">
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <Ticket className="w-3.5 h-3.5 text-accent-primary" />
              <span>
                {query ? `Tickets matching "${query}"` : 'Recent tickets'}
              </span>
            </div>
          </div>

          {/* List */}
          <div ref={listRef} className="max-h-48 overflow-y-auto">
            {isLoading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-accent-primary" />
              </div>
            )}

            {!isLoading && tickets.length === 0 && (
              <div className="py-4 px-3 text-center text-xs text-text-muted">
                {query ? 'No tickets found' : 'No recent tickets'}
              </div>
            )}

            {!isLoading &&
              tickets.map((ticket, index) => (
                <button
                  key={ticket.id}
                  onClick={() => onSelect(ticket)}
                  className={cn(
                    'w-full px-3 py-2 text-left hover:bg-bg-tertiary transition-colors flex items-center gap-2',
                    index === selectedIndex && 'bg-accent-primary/10'
                  )}
                >
                  <span className="font-medium text-accent-primary text-xs">
                    #{ticket.ticket_number}
                  </span>
                  {statusIcons[ticket.status as keyof typeof statusIcons]}
                  <span className="flex-1 truncate text-xs text-text-primary">
                    {ticket.title}
                  </span>
                  <span
                    className={cn(
                      'px-1.5 py-0.5 rounded text-[9px] font-medium',
                      priorityColors[ticket.priority as keyof typeof priorityColors]
                    )}
                  >
                    {ticket.priority}
                  </span>
                </button>
              ))}
          </div>

          {/* Footer hint */}
          <div className="px-3 py-1.5 border-t border-border-primary bg-bg-secondary/30">
            <div className="flex items-center gap-3 text-[10px] text-text-muted">
              <span>
                <kbd className="px-1 py-0.5 rounded bg-bg-tertiary">↑↓</kbd> navigate
              </span>
              <span>
                <kbd className="px-1 py-0.5 rounded bg-bg-tertiary">Enter</kbd> select
              </span>
              <span>
                <kbd className="px-1 py-0.5 rounded bg-bg-tertiary">Esc</kbd> close
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
})
