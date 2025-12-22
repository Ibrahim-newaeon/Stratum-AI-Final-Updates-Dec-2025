/**
 * Landing Page CMS
 * Manage landing page content with multi-language support
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Globe,
  Save,
  Eye,
  EyeOff,
  History,
  RotateCcw,
  RefreshCw,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  FileText,
  Sparkles,
  Layout,
  BarChart3,
  Star,
  CreditCard,
  MessageSquare,
  Megaphone,
  Search as SearchIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// Types
interface ContentSection {
  id: number
  section: string
  language: string
  content: Record<string, unknown>
  is_published: boolean
  version: number
  created_at: string
  updated_at: string
  published_at: string | null
  updated_by: number | null
}

interface HistoryItem {
  id: number
  content_id: number
  section: string
  language: string
  content: Record<string, unknown>
  version: number
  changed_by: number | null
  created_at: string
}

// Section icons mapping
const sectionIcons: Record<string, typeof FileText> = {
  hero: Sparkles,
  stats: BarChart3,
  features: Layout,
  pricing: CreditCard,
  testimonials: MessageSquare,
  cta: Star,
  seo: SearchIcon,
  announcement: Megaphone,
}

// API base URL
const API_BASE = '/api/v1/landing-cms'

export default function LandingCMS() {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [languages, setLanguages] = useState<string[]>([])
  const [sections, setSections] = useState<string[]>([])
  const [selectedLanguage, setSelectedLanguage] = useState('en')
  const [selectedSection, setSelectedSection] = useState('')
  const [content, setContent] = useState<ContentSection | null>(null)
  const [editedContent, setEditedContent] = useState<string>('')
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // Fetch token for authenticated requests
  const getHeaders = useCallback(() => {
    const token = localStorage.getItem('access_token')
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }
  }, [])

  // Show notification
  const showNotification = useCallback((type: 'success' | 'error', message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 3000)
  }, [])

  // Fetch available languages and sections
  const fetchMetadata = useCallback(async () => {
    try {
      const [langRes, secRes] = await Promise.all([
        fetch(`${API_BASE}/languages`, { headers: getHeaders() }),
        fetch(`${API_BASE}/sections`, { headers: getHeaders() }),
      ])

      if (langRes.ok) {
        const langData = await langRes.json()
        setLanguages(langData)
      }

      if (secRes.ok) {
        const secData = await secRes.json()
        setSections(secData)
        if (secData.length > 0 && !selectedSection) {
          setSelectedSection(secData[0])
        }
      }
    } catch (err) {
      console.error('Failed to fetch metadata:', err)
    }
  }, [getHeaders, selectedSection])

  // Fetch section content
  const fetchContent = useCallback(async () => {
    if (!selectedSection || !selectedLanguage) return

    setIsLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/admin/section/${selectedSection}/${selectedLanguage}`,
        { headers: getHeaders() }
      )

      if (res.ok) {
        const data = await res.json()
        setContent(data)
        setEditedContent(JSON.stringify(data.content, null, 2))
        setHasChanges(false)
      } else if (res.status === 404) {
        setContent(null)
        setEditedContent('{}')
      }
    } catch (err) {
      console.error('Failed to fetch content:', err)
      showNotification('error', 'Failed to load content')
    } finally {
      setIsLoading(false)
    }
  }, [selectedSection, selectedLanguage, getHeaders, showNotification])

  // Fetch version history
  const fetchHistory = useCallback(async () => {
    if (!selectedSection || !selectedLanguage) return

    try {
      const res = await fetch(
        `${API_BASE}/admin/section/${selectedSection}/${selectedLanguage}/history?limit=10`,
        { headers: getHeaders() }
      )

      if (res.ok) {
        const data = await res.json()
        setHistory(data)
      }
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }, [selectedSection, selectedLanguage, getHeaders])

  // Save content
  const saveContent = async () => {
    if (!selectedSection || !selectedLanguage) return

    try {
      JSON.parse(editedContent) // Validate JSON
    } catch {
      showNotification('error', 'Invalid JSON format')
      return
    }

    setIsSaving(true)
    try {
      const res = await fetch(
        `${API_BASE}/admin/section/${selectedSection}/${selectedLanguage}`,
        {
          method: 'PUT',
          headers: getHeaders(),
          body: JSON.stringify({
            content: JSON.parse(editedContent),
            is_published: content?.is_published,
          }),
        }
      )

      if (res.ok) {
        const data = await res.json()
        setContent(data)
        setHasChanges(false)
        showNotification('success', 'Content saved successfully')
        fetchHistory()
      } else {
        const err = await res.json()
        showNotification('error', err.detail || 'Failed to save')
      }
    } catch (err) {
      showNotification('error', 'Failed to save content')
    } finally {
      setIsSaving(false)
    }
  }

  // Publish/Unpublish
  const togglePublish = async () => {
    if (!selectedSection || !selectedLanguage || !content) return

    const action = content.is_published ? 'unpublish' : 'publish'

    try {
      const res = await fetch(
        `${API_BASE}/admin/section/${selectedSection}/${selectedLanguage}/${action}`,
        { method: 'POST', headers: getHeaders() }
      )

      if (res.ok) {
        const data = await res.json()
        setContent(data)
        showNotification('success', `Content ${action}ed successfully`)
      }
    } catch (err) {
      showNotification('error', `Failed to ${action} content`)
    }
  }

  // Rollback to version
  const rollback = async (version: number) => {
    if (!selectedSection || !selectedLanguage) return

    try {
      const res = await fetch(
        `${API_BASE}/admin/section/${selectedSection}/${selectedLanguage}/rollback/${version}`,
        { method: 'POST', headers: getHeaders() }
      )

      if (res.ok) {
        const data = await res.json()
        setContent(data)
        setEditedContent(JSON.stringify(data.content, null, 2))
        setHasChanges(false)
        setShowHistory(false)
        showNotification('success', `Rolled back to version ${version}`)
        fetchHistory()
      }
    } catch (err) {
      showNotification('error', 'Failed to rollback')
    }
  }

  // Initial load
  useEffect(() => {
    fetchMetadata()
  }, [fetchMetadata])

  // Fetch content when selection changes
  useEffect(() => {
    fetchContent()
  }, [fetchContent])

  // Track changes
  useEffect(() => {
    if (content) {
      const originalContent = JSON.stringify(content.content, null, 2)
      setHasChanges(editedContent !== originalContent)
    }
  }, [editedContent, content])

  // Language display names
  const languageNames: Record<string, string> = {
    en: 'English',
    ar: 'العربية',
  }

  const SectionIcon = sectionIcons[selectedSection] || FileText

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Globe className="w-7 h-7 text-primary" />
            Landing Page CMS
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage landing page content with multi-language support
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <div className="relative">
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="appearance-none pl-10 pr-8 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 font-medium"
            >
              {languages.map((lang) => (
                <option key={lang} value={lang}>
                  {languageNames[lang] || lang.toUpperCase()}
                </option>
              ))}
            </select>
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          </div>

          {/* History Toggle */}
          <button
            onClick={() => {
              setShowHistory(!showHistory)
              if (!showHistory) fetchHistory()
            }}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors',
              showHistory ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
            )}
          >
            <History className="w-4 h-4" />
            History
          </button>

          {/* Preview Button */}
          <a
            href={`/?preview=true&lang=${selectedLanguage}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <Eye className="w-4 h-4" />
            Preview
          </a>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div
          className={cn(
            'flex items-center gap-2 px-4 py-3 rounded-lg',
            notification.type === 'success'
              ? 'bg-green-500/10 text-green-600 border border-green-500/20'
              : 'bg-red-500/10 text-red-600 border border-red-500/20'
          )}
        >
          {notification.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {notification.message}
        </div>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Section Sidebar */}
        <div className="col-span-12 lg:col-span-3">
          <div className="rounded-xl border bg-card p-4 space-y-2">
            <h3 className="font-semibold text-sm text-muted-foreground px-2 mb-3">
              SECTIONS
            </h3>
            {sections.map((section) => {
              const Icon = sectionIcons[section] || FileText
              return (
                <button
                  key={section}
                  onClick={() => setSelectedSection(section)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors capitalize',
                    selectedSection === section
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {section.replace(/_/g, ' ')}
                </button>
              )
            })}
          </div>
        </div>

        {/* Content Editor */}
        <div className="col-span-12 lg:col-span-9">
          {showHistory ? (
            /* History Panel */
            <div className="rounded-xl border bg-card p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <History className="w-5 h-5 text-primary" />
                Version History - {selectedSection} ({selectedLanguage})
              </h3>

              {history.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No history available for this section.
                </p>
              ) : (
                <div className="space-y-3">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/30 transition-colors"
                    >
                      <div>
                        <p className="font-medium">Version {item.version}</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={() => rollback(item.version)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border hover:bg-muted transition-colors text-sm"
                      >
                        <RotateCcw className="w-4 h-4" />
                        Restore
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Editor Panel */
            <div className="rounded-xl border bg-card">
              {/* Editor Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b">
                <div className="flex items-center gap-3">
                  <SectionIcon className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold capitalize">
                    {selectedSection.replace(/_/g, ' ')}
                  </h3>
                  {content && (
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        content.is_published
                          ? 'bg-green-500/10 text-green-600'
                          : 'bg-amber-500/10 text-amber-600'
                      )}
                    >
                      {content.is_published ? 'Published' : 'Draft'}
                    </span>
                  )}
                  {content && (
                    <span className="text-xs text-muted-foreground">
                      v{content.version}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {content && (
                    <button
                      onClick={togglePublish}
                      className={cn(
                        'flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors text-sm',
                        content.is_published
                          ? 'hover:bg-amber-500/10 hover:border-amber-500/30'
                          : 'hover:bg-green-500/10 hover:border-green-500/30'
                      )}
                    >
                      {content.is_published ? (
                        <>
                          <EyeOff className="w-4 h-4" />
                          Unpublish
                        </>
                      ) : (
                        <>
                          <Eye className="w-4 h-4" />
                          Publish
                        </>
                      )}
                    </button>
                  )}

                  <button
                    onClick={saveContent}
                    disabled={!hasChanges || isSaving}
                    className={cn(
                      'flex items-center gap-2 px-4 py-1.5 rounded-lg transition-colors text-sm font-medium',
                      hasChanges
                        ? 'bg-gradient-stratum text-white shadow-glow hover:shadow-glow-lg'
                        : 'bg-muted text-muted-foreground cursor-not-allowed'
                    )}
                  >
                    {isSaving ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>

              {/* JSON Editor */}
              <div className="p-6">
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <RefreshCw className="w-8 h-8 animate-spin text-primary" />
                  </div>
                ) : content ? (
                  <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className={cn(
                      'w-full h-[500px] font-mono text-sm p-4 rounded-lg border bg-muted/30 focus:ring-2 focus:ring-primary/20 resize-none',
                      selectedLanguage === 'ar' && 'text-right'
                    )}
                    dir={selectedLanguage === 'ar' ? 'rtl' : 'ltr'}
                    spellCheck={false}
                  />
                ) : (
                  <div className="text-center py-12">
                    <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground">
                      No content found for this section in {languageNames[selectedLanguage] || selectedLanguage}.
                    </p>
                    <button
                      onClick={() => {
                        // Create new section
                        fetch(`${API_BASE}/admin/section`, {
                          method: 'POST',
                          headers: getHeaders(),
                          body: JSON.stringify({
                            section: selectedSection,
                            language: selectedLanguage,
                            content: {},
                          }),
                        })
                          .then((res) => res.json())
                          .then((data) => {
                            setContent(data)
                            setEditedContent(JSON.stringify(data.content, null, 2))
                            showNotification('success', 'Section created')
                          })
                          .catch(() => showNotification('error', 'Failed to create section'))
                      }}
                      className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                    >
                      Create Section
                    </button>
                  </div>
                )}

                {/* Content Structure Help */}
                {content && selectedSection && (
                  <div className="mt-4 p-4 rounded-lg bg-muted/30 border border-dashed">
                    <p className="text-sm text-muted-foreground">
                      <strong>Tip:</strong> Edit the JSON above to update the content.
                      The structure varies by section. Make sure to maintain valid JSON format.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
