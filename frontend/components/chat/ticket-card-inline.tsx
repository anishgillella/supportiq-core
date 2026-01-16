'use client'

import { Ticket, ExternalLink, Clock, AlertCircle, CheckCircle, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'
import Link from 'next/link'

interface TicketCardInlineProps {
  id: string
  ticketNumber: number
  title: string
  status: string
  priority: string
  isCreated?: boolean // Highlight if just created
}

const priorityColors = {
  low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  medium: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
}

const statusIcons = {
  open: <Circle className="w-3 h-3 text-yellow-400" />,
  in_progress: <Clock className="w-3 h-3 text-blue-400" />,
  resolved: <CheckCircle className="w-3 h-3 text-green-400" />,
  closed: <CheckCircle className="w-3 h-3 text-gray-400" />,
}

const statusLabels = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
}

export function TicketCardInline({
  id,
  ticketNumber,
  title,
  status,
  priority,
  isCreated,
}: TicketCardInlineProps) {
  return (
    <div
      className={cn(
        'mt-2 p-3 rounded-lg border bg-bg-tertiary/50',
        isCreated ? 'border-green-500/50 bg-green-500/5' : 'border-border-primary'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={cn(
            'p-1.5 rounded-md',
            isCreated ? 'bg-green-500/20' : 'bg-accent-primary/20'
          )}>
            <Ticket className={cn(
              'w-4 h-4',
              isCreated ? 'text-green-400' : 'text-accent-primary'
            )} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-text-primary text-sm">
                Ticket #{ticketNumber}
              </span>
              {isCreated && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 font-medium">
                  Created
                </span>
              )}
            </div>
            <p className="text-xs text-text-muted truncate" title={title}>
              {title}
            </p>
          </div>
        </div>
        <Link
          href={`/dashboard/tickets/${id}`}
          className="p-1.5 rounded hover:bg-bg-secondary transition-colors flex-shrink-0"
          title="View ticket"
        >
          <ExternalLink className="w-4 h-4 text-text-muted hover:text-accent-primary" />
        </Link>
      </div>

      <div className="flex items-center gap-3 mt-2 pt-2 border-t border-border-primary/50">
        <div className="flex items-center gap-1.5">
          {statusIcons[status as keyof typeof statusIcons] || statusIcons.open}
          <span className="text-xs text-text-muted">
            {statusLabels[status as keyof typeof statusLabels] || status}
          </span>
        </div>
        <span
          className={cn(
            'px-2 py-0.5 rounded text-[10px] font-medium border',
            priorityColors[priority as keyof typeof priorityColors] || priorityColors.medium
          )}
        >
          {priority.charAt(0).toUpperCase() + priority.slice(1)}
        </span>
      </div>
    </div>
  )
}
