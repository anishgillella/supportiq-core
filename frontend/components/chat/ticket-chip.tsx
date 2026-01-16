'use client'

import { X, Ticket } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TicketChipProps {
  ticketNumber: number
  title: string
  status: string
  priority: string
  onRemove?: () => void
  onClick?: () => void
  className?: string
}

const priorityColors = {
  low: 'bg-gray-500/20 text-gray-400',
  medium: 'bg-blue-500/20 text-blue-400',
  high: 'bg-orange-500/20 text-orange-400',
  critical: 'bg-red-500/20 text-red-400',
}

const statusColors = {
  open: 'border-yellow-500/50',
  in_progress: 'border-blue-500/50',
  resolved: 'border-green-500/50',
  closed: 'border-gray-500/50',
}

export function TicketChip({
  ticketNumber,
  title,
  status,
  priority,
  onRemove,
  onClick,
  className,
}: TicketChipProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border bg-bg-tertiary text-xs',
        statusColors[status as keyof typeof statusColors] || 'border-border-primary',
        onClick && 'cursor-pointer hover:bg-bg-secondary transition-colors',
        className
      )}
      onClick={onClick}
    >
      <Ticket className="w-3 h-3 text-text-muted flex-shrink-0" />
      <span className="font-medium text-text-primary">#{ticketNumber}</span>
      <span className="text-text-muted truncate max-w-[120px]" title={title}>
        {title}
      </span>
      <span
        className={cn(
          'px-1.5 py-0.5 rounded text-[10px] font-medium',
          priorityColors[priority as keyof typeof priorityColors] || 'bg-gray-500/20 text-gray-400'
        )}
      >
        {priority}
      </span>
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onRemove()
          }}
          className="ml-0.5 p-0.5 rounded hover:bg-bg-primary transition-colors"
        >
          <X className="w-3 h-3 text-text-muted hover:text-text-primary" />
        </button>
      )}
    </div>
  )
}
