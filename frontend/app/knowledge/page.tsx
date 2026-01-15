'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Globe, FileText, Trash2, Loader2, Plus, Database, MessageSquare, Phone, PhoneCall, PhoneOff, Mic, MicOff } from 'lucide-react'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import Vapi from '@vapi-ai/web'

interface Document {
  id: string
  title: string
  source: string
  source_type: string
  chunks_count: number
  created_at: string
}

// VAPI Configuration - loaded from environment variables
const VAPI_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY!
const VAPI_ASSISTANT_ID = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID!

export default function KnowledgePage() {
  const router = useRouter()
  const { token, userId } = useOnboardingStore()
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [isScraping, setIsScraping] = useState(false)
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isHydrated, setIsHydrated] = useState(false)

  // Voice call state
  const [showCallModal, setShowCallModal] = useState(false)
  const [isCallActive, setIsCallActive] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [volumeLevel, setVolumeLevel] = useState(0)
  const [callStatus, setCallStatus] = useState<string>('Ready to call')
  const vapiRef = useRef<Vapi | null>(null)

  // Initialize VAPI
  useEffect(() => {
    if (typeof window !== 'undefined' && !vapiRef.current) {
      vapiRef.current = new Vapi(VAPI_PUBLIC_KEY)

      // Set up event listeners
      vapiRef.current.on('call-start', () => {
        setIsCallActive(true)
        setIsConnecting(false)
        setCallStatus('Connected - Speak now')
      })

      vapiRef.current.on('call-end', () => {
        setIsCallActive(false)
        setIsConnecting(false)
        setCallStatus('Call ended')
        setVolumeLevel(0)
        setTimeout(() => {
          setShowCallModal(false)
          setCallStatus('Ready to call')
        }, 2000)
      })

      vapiRef.current.on('volume-level', (level: number) => {
        setVolumeLevel(level)
      })

      vapiRef.current.on('error', (error: any) => {
        console.error('VAPI Error:', JSON.stringify(error, null, 2))
        const errorMessage = error?.message || error?.error?.message || 'Connection failed'
        setCallStatus(`Error: ${errorMessage}`)
        setIsConnecting(false)
        setIsCallActive(false)
      })

      vapiRef.current.on('speech-start', () => {
        setCallStatus('Assistant is speaking...')
      })

      vapiRef.current.on('speech-end', () => {
        setCallStatus('Listening...')
      })
    }

    return () => {
      if (vapiRef.current) {
        vapiRef.current.stop()
      }
    }
  }, [])

  // Wait for Zustand to hydrate from localStorage
  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (!isHydrated || !token) return
    loadDocuments()
  }, [token, isHydrated])

  const loadDocuments = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await api.getKnowledgeBase(token)
      setDocuments(response.documents)
    } catch (err) {
      console.error('Failed to load documents:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !token) return

    setIsUploading(true)
    setError(null)

    try {
      await api.uploadDocument(token, file)
      await loadDocuments()
      setShowAddModal(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleScrapeWebsite = async () => {
    if (!websiteUrl || !token) return

    setIsScraping(true)
    setError(null)

    try {
      await api.scrapeWebsite(token, websiteUrl)
      await loadDocuments()
      setWebsiteUrl('')
      setShowAddModal(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scraping failed')
    } finally {
      setIsScraping(false)
    }
  }

  const handleDeleteDocument = async (documentId: string) => {
    if (!token) return

    try {
      await api.deleteDocument(token, documentId)
      setDocuments(prev => prev.filter(d => d.id !== documentId))
    } catch (err) {
      console.error('Failed to delete document:', err)
    }
  }

  const handleStartCall = useCallback(async () => {
    if (!vapiRef.current) return

    setShowCallModal(true)
    setIsConnecting(true)
    setCallStatus('Connecting...')

    try {
      await vapiRef.current.start(VAPI_ASSISTANT_ID, {
        metadata: {
          user_id: userId,
          initiated_from: 'knowledge_base'
        }
      })
    } catch (err) {
      console.error('Failed to start call:', err)
      setCallStatus('Failed to connect')
      setIsConnecting(false)
    }
  }, [userId])

  const handleEndCall = useCallback(() => {
    if (vapiRef.current) {
      vapiRef.current.stop()
    }
  }, [])

  const handleToggleMute = useCallback(() => {
    if (vapiRef.current) {
      const newMuted = !isMuted
      vapiRef.current.setMuted(newMuted)
      setIsMuted(newMuted)
    }
  }, [isMuted])

  return (
    <AuthenticatedLayout>
      <div className="min-h-screen bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary">
      {/* Header */}
      <header className="border-b border-border-primary bg-bg-secondary/50 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-text-primary">Knowledge Base</h1>
              <p className="text-xs text-text-muted">Manage your AI's knowledge</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleStartCall}
              disabled={documents.length === 0}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 text-white font-medium hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              title={documents.length === 0 ? 'Add documents first to use voice agent' : 'Start a voice call with your AI agent'}
            >
              <PhoneCall className="w-4 h-4" />
              Start Call
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border-primary text-text-secondary hover:bg-bg-tertiary transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              Open Chat
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-primary text-white font-medium hover:bg-accent-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Content
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-accent-primary" />
          </div>
        ) : documents.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 flex items-center justify-center mx-auto mb-6">
              <Database className="w-10 h-10 text-green-500" />
            </div>
            <h2 className="text-2xl font-semibold text-text-primary mb-2">
              Your knowledge base is empty
            </h2>
            <p className="text-text-muted max-w-md mx-auto mb-6">
              Add documents or scrape websites to train your AI assistant with your company's information.
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-accent-primary text-white font-medium hover:bg-accent-primary/90 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Add Your First Document
            </button>
          </motion.div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence>
              {documents.map((doc) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-bg-secondary rounded-xl border border-border-primary p-4 hover:border-accent-primary/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 rounded-lg bg-bg-tertiary flex items-center justify-center">
                      {doc.source_type === 'website' ? (
                        <Globe className="w-5 h-5 text-blue-500" />
                      ) : (
                        <FileText className="w-5 h-5 text-orange-500" />
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="p-2 rounded-lg hover:bg-error/10 text-text-muted hover:text-error transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <h3 className="font-medium text-text-primary mb-1 line-clamp-2">
                    {doc.title}
                  </h3>
                  <p className="text-xs text-text-muted mb-3 line-clamp-1">
                    {doc.source}
                  </p>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-muted">
                      {doc.chunks_count} chunks
                    </span>
                    <span className="text-text-muted">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </main>

      {/* Voice Call Modal */}
      <AnimatePresence>
        {showCallModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-bg-secondary rounded-2xl border border-border-primary p-8 max-w-sm w-full text-center"
            >
              {/* Voice visualization */}
              <div className="relative w-32 h-32 mx-auto mb-6">
                {/* Pulsing rings based on volume */}
                <motion.div
                  className="absolute inset-0 rounded-full bg-green-500/20"
                  animate={{
                    scale: isCallActive ? [1, 1.2 + volumeLevel * 0.5, 1] : 1,
                    opacity: isCallActive ? [0.5, 0.2, 0.5] : 0.3,
                  }}
                  transition={{
                    duration: 0.5,
                    repeat: isCallActive ? Infinity : 0,
                    ease: 'easeInOut',
                  }}
                />
                <motion.div
                  className="absolute inset-2 rounded-full bg-green-500/30"
                  animate={{
                    scale: isCallActive ? [1, 1.1 + volumeLevel * 0.3, 1] : 1,
                    opacity: isCallActive ? [0.6, 0.3, 0.6] : 0.4,
                  }}
                  transition={{
                    duration: 0.5,
                    repeat: isCallActive ? Infinity : 0,
                    ease: 'easeInOut',
                    delay: 0.1,
                  }}
                />
                {/* Center icon */}
                <div className={`absolute inset-4 rounded-full flex items-center justify-center ${
                  isCallActive ? 'bg-gradient-to-br from-green-500 to-emerald-600' :
                  isConnecting ? 'bg-gradient-to-br from-yellow-500 to-orange-500' :
                  'bg-gradient-to-br from-gray-500 to-gray-600'
                }`}>
                  {isConnecting ? (
                    <Loader2 className="w-10 h-10 text-white animate-spin" />
                  ) : isCallActive ? (
                    <Phone className="w-10 h-10 text-white" />
                  ) : (
                    <PhoneOff className="w-10 h-10 text-white" />
                  )}
                </div>
              </div>

              {/* Status text */}
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                Voice Assistant
              </h3>
              <p className="text-sm text-text-muted mb-6">
                {callStatus}
              </p>

              {/* Controls */}
              <div className="flex items-center justify-center gap-4">
                {isCallActive && (
                  <button
                    onClick={handleToggleMute}
                    className={`p-4 rounded-full transition-colors ${
                      isMuted
                        ? 'bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30'
                        : 'bg-bg-tertiary text-text-secondary hover:bg-bg-tertiary/80'
                    }`}
                    title={isMuted ? 'Unmute' : 'Mute'}
                  >
                    {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
                  </button>
                )}

                {isCallActive || isConnecting ? (
                  <button
                    onClick={handleEndCall}
                    className="p-4 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors"
                    title="End call"
                  >
                    <PhoneOff className="w-6 h-6" />
                  </button>
                ) : (
                  <button
                    onClick={() => setShowCallModal(false)}
                    className="px-6 py-3 rounded-lg border border-border-primary text-text-secondary hover:bg-bg-tertiary transition-colors"
                  >
                    Close
                  </button>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add Content Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-bg-secondary rounded-2xl border border-border-primary p-6 max-w-lg w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-semibold text-text-primary mb-6">
                Add to Knowledge Base
              </h2>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm">
                  {error}
                </div>
              )}

              {/* Scrape Website */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-text-primary mb-2 flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  Scrape Website
                </h3>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="flex-1 px-4 py-2 rounded-lg bg-bg-tertiary border border-border-primary text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                    disabled={isScraping}
                  />
                  <button
                    onClick={handleScrapeWebsite}
                    disabled={!websiteUrl || isScraping}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {isScraping ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Globe className="w-4 h-4" />
                    )}
                    Scrape
                  </button>
                </div>
              </div>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border-primary"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 bg-bg-secondary text-text-muted">or</span>
                </div>
              </div>

              {/* Upload File */}
              <div>
                <h3 className="text-sm font-medium text-text-primary mb-2 flex items-center gap-2">
                  <Upload className="w-4 h-4" />
                  Upload Document
                </h3>
                <label className="block">
                  <div className="border-2 border-dashed border-border-primary rounded-lg p-8 text-center hover:border-accent-primary/50 transition-colors cursor-pointer">
                    {isUploading ? (
                      <Loader2 className="w-8 h-8 animate-spin text-accent-primary mx-auto" />
                    ) : (
                      <>
                        <Upload className="w-8 h-8 text-text-muted mx-auto mb-2" />
                        <p className="text-text-primary font-medium">
                          Click to upload
                        </p>
                        <p className="text-xs text-text-muted mt-1">
                          TXT, MD files supported
                        </p>
                      </>
                    )}
                  </div>
                  <input
                    type="file"
                    accept=".txt,.md"
                    onChange={handleFileUpload}
                    className="hidden"
                    disabled={isUploading}
                  />
                </label>
              </div>

              <button
                onClick={() => setShowAddModal(false)}
                className="w-full mt-6 px-4 py-2 rounded-lg border border-border-primary text-text-secondary hover:bg-bg-tertiary transition-colors"
              >
                Cancel
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
    </AuthenticatedLayout>
  )
}
