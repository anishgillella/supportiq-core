'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare,
  Plus,
  Trash2,
  ChevronRight,
  Ticket,
  Clock,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  attached_ticket_ids: string[]
}

interface ChatHistorySidebarProps {
  conversations: Conversation[]
  activeConversationId: string | null
  isLoading: boolean
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  onDeleteConversation: (id: string) => void
}

// Group conversations by date
function groupByDate(conversations: Conversation[]): Record<string, Conversation[]> {
  const groups: Record<string, Conversation[]> = {
    Today: [],
    Yesterday: [],
    'This Week': [],
    'This Month': [],
    Older: [],
  }

  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
  const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

  conversations.forEach((conv) => {
    const date = new Date(conv.updated_at)

    if (date >= today) {
      groups.Today.push(conv)
    } else if (date >= yesterday) {
      groups.Yesterday.push(conv)
    } else if (date >= weekAgo) {
      groups['This Week'].push(conv)
    } else if (date >= monthAgo) {
      groups['This Month'].push(conv)
    } else {
      groups.Older.push(conv)
    }
  })

  // Remove empty groups
  Object.keys(groups).forEach((key) => {
    if (groups[key].length === 0) {
      delete groups[key]
    }
  })

  return groups
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
}: {
  conversation: Conversation
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const [showDelete, setShowDelete] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={onSelect}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect()
        }
      }}
      className={cn(
        'w-full text-left px-3 py-2.5 rounded-lg transition-colors group relative cursor-pointer',
        isActive
          ? 'bg-accent-primary/20 text-text-primary'
          : 'hover:bg-bg-tertiary text-text-secondary'
      )}
    >
      <div className="flex items-start gap-2">
        <MessageSquare
          className={cn(
            'w-4 h-4 mt-0.5 flex-shrink-0',
            isActive ? 'text-accent-primary' : 'text-text-muted'
          )}
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium truncate">{conversation.title || 'New Chat'}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-text-muted">
              {new Date(conversation.updated_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            {conversation.attached_ticket_ids.length > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] text-text-muted">
                <Ticket className="w-3 h-3" />
                {conversation.attached_ticket_ids.length}
              </span>
            )}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showDelete && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md hover:bg-red-500/20 text-text-muted hover:text-red-400 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function ChatHistorySidebar({
  conversations,
  activeConversationId,
  isLoading,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
}: ChatHistorySidebarProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})

  const groupedConversations = useMemo(() => groupByDate(conversations), [conversations])

  const toggleGroup = (group: string) => {
    setCollapsedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }))
  }

  return (
    <div className="w-64 h-full bg-bg-secondary border-r border-border-primary flex flex-col">
      {/* New Chat Button */}
      <div className="p-3 border-b border-border-primary">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent-primary text-white font-medium hover:bg-accent-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
          </div>
        ) : Object.keys(groupedConversations).length === 0 ? (
          <div className="text-center py-8">
            <Clock className="w-8 h-8 text-text-muted mx-auto mb-2" />
            <p className="text-sm text-text-muted">No chat history</p>
            <p className="text-xs text-text-muted mt-1">Start a new conversation</p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(groupedConversations).map(([group, convs]) => (
              <div key={group}>
                <button
                  onClick={() => toggleGroup(group)}
                  className="flex items-center gap-1 px-2 py-1 text-xs font-semibold text-text-muted uppercase tracking-wider w-full hover:text-text-secondary transition-colors"
                >
                  <ChevronRight
                    className={cn(
                      'w-3 h-3 transition-transform',
                      !collapsedGroups[group] && 'rotate-90'
                    )}
                  />
                  {group}
                  <span className="text-text-muted/50 ml-auto">{convs.length}</span>
                </button>

                <AnimatePresence>
                  {!collapsedGroups[group] && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="space-y-1 mt-1"
                    >
                      {convs.map((conv) => (
                        <ConversationItem
                          key={conv.id}
                          conversation={conv}
                          isActive={conv.id === activeConversationId}
                          onSelect={() => onSelectConversation(conv.id)}
                          onDelete={() => onDeleteConversation(conv.id)}
                        />
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
