'use client'

import { Sidebar } from './sidebar'

interface PublicLayoutProps {
  children: React.ReactNode
}

export function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Sidebar />
      <main className="lg:ml-[260px] min-h-screen">
        {children}
      </main>
    </div>
  )
}
