'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Globe, FileText, Trash2, Loader2, Plus, Database } from 'lucide-react'
import { useOnboardingStore } from '@/stores/onboarding-store'
import { api } from '@/lib/api'

interface Document {
  id: string
  title: string
  source: string
  source_type: string
  chunks_count: number
  created_at: string
}

export default function KnowledgePage() {
  const router = useRouter()
  const { token } = useOnboardingStore()
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [isScraping, setIsScraping] = useState(false)
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      router.push('/login')
      return
    }
    loadDocuments()
  }, [token, router])

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

  if (!token) return null

  return (
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
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-primary text-white font-medium hover:bg-accent-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Content
          </button>
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
  )
}
