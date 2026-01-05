import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search,
  Plus,
  MoreHorizontal,
  MessageCircle,
  Users,
  FileText,
  Send,
  CheckCircle,
  Clock,
  XCircle,
  Phone,
  UserCheck,
  UserX,
  Eye,
  Radio,
  Trash2,
  Upload,
  Inbox,
  Reply,
  ArrowLeft,
  Paperclip,
  Image,
  Smile,
  FileSpreadsheet,
  Download,
  AlertCircle,
  X,
  ChevronDown,
  Globe,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/api/client'

// Types
interface WhatsAppContact {
  id: number
  phone_number: string
  country_code: string
  display_name: string | null
  is_verified: boolean
  opt_in_status: 'opted_in' | 'pending' | 'opted_out'
  wa_id: string | null
  profile_name: string | null
  message_count: number
  last_message_at: string | null
  created_at: string
}

interface WhatsAppTemplate {
  id: number
  name: string
  language: string
  category: string
  body_text: string
  status: 'approved' | 'pending' | 'rejected' | 'paused'
  usage_count: number
  created_at: string
}

interface WhatsAppMessage {
  id: number
  contact_id: number
  direction: 'inbound' | 'outbound'
  message_type: string
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
  content: string | null
  template_name: string | null
  sent_at: string | null
  delivered_at: string | null
  read_at: string | null
  created_at: string
}

type OptInStatus = 'opted_in' | 'pending' | 'opted_out'
type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
type TemplateStatus = 'approved' | 'pending' | 'rejected' | 'paused'

type TabType = 'inbox' | 'contacts' | 'templates' | 'messages'
type AddContactTab = 'single' | 'csv'

// CSV parsed contact type
interface CSVContact {
  phone_number: string
  country_code: string
  display_name: string
  isValid: boolean
  error?: string
}

// Conversation type for inbox
interface Conversation {
  id: number
  contact: WhatsAppContact
  lastMessage: WhatsAppMessage | null
  unreadCount: number
  isActive: boolean
}

export function WhatsApp() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabType>('contacts')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [contacts, setContacts] = useState<WhatsAppContact[]>([])
  const [templates, setTemplates] = useState<WhatsAppTemplate[]>([])
  const [messages, setMessages] = useState<WhatsAppMessage[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [showNewContactModal, setShowNewContactModal] = useState(false)
  const [showBroadcastModal, setShowBroadcastModal] = useState(false)
  const [selectedContactIds, setSelectedContactIds] = useState<number[]>([])
  const [broadcastTemplate, setBroadcastTemplate] = useState<string>('')
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [chatMessages, setChatMessages] = useState<WhatsAppMessage[]>([])
  const [replyText, setReplyText] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // New contact modal state
  const [addContactTab, setAddContactTab] = useState<AddContactTab>('single')
  const [csvContacts, setCsvContacts] = useState<CSVContact[]>([])
  const [csvFileName, setCsvFileName] = useState<string>('')
  const [isDragging, setIsDragging] = useState(false)
  const [csvError, setCsvError] = useState<string>('')
  const [isImporting, setIsImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Single contact form state
  const [newContactPhone, setNewContactPhone] = useState('')
  const [newContactCountry, setNewContactCountry] = useState('')
  const [newContactName, setNewContactName] = useState('')

  // Fetch data on mount
  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [contactsRes, templatesRes, messagesRes] = await Promise.all([
        apiClient.get('/whatsapp/contacts'),
        apiClient.get('/whatsapp/templates'),
        apiClient.get('/whatsapp/messages'),
      ])

      const contactsList = contactsRes.data?.data?.items || []
      const templatesList = templatesRes.data?.data?.items || []
      const messagesList = messagesRes.data?.data?.items || []

      setContacts(contactsList)
      setTemplates(templatesList)
      setMessages(messagesList)

      // Build conversations from contacts and messages
      const convos: Conversation[] = contactsList
        .filter((c: WhatsAppContact) => c.message_count > 0)
        .map((contact: WhatsAppContact) => {
          const contactMessages = messagesList.filter((m: WhatsAppMessage) => m.contact_id === contact.id)
          const lastMessage = contactMessages.length > 0
            ? contactMessages.sort((a: WhatsAppMessage, b: WhatsAppMessage) =>
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
              )[0]
            : null
          const unreadCount = contactMessages.filter(
            (m: WhatsAppMessage) => m.direction === 'inbound' && m.status !== 'read'
          ).length

          return {
            id: contact.id,
            contact,
            lastMessage,
            unreadCount,
            isActive: contact.last_message_at
              ? new Date().getTime() - new Date(contact.last_message_at).getTime() < 24 * 60 * 60 * 1000
              : false,
          }
        })

      setConversations(convos)
    } catch (err: any) {
      console.error('Failed to fetch WhatsApp data:', err)
      setError(err.response?.data?.detail || 'Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch messages for a specific contact
  const fetchContactMessages = async (contactId: number) => {
    try {
      const response = await apiClient.get(`/whatsapp/messages?contact_id=${contactId}`)
      const messages = response.data?.data?.items || []
      setChatMessages(messages.sort((a: WhatsAppMessage, b: WhatsAppMessage) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ))
    } catch (err) {
      console.error('Failed to fetch messages:', err)
    }
  }

  // Toggle single contact selection
  const toggleContactSelection = (contactId: number) => {
    setSelectedContactIds((prev) =>
      prev.includes(contactId)
        ? prev.filter((id) => id !== contactId)
        : [...prev, contactId]
    )
  }

  // Toggle select all (only opted-in contacts)
  const toggleSelectAll = () => {
    const optedInContacts = filteredContacts.filter((c) => c.opt_in_status === 'opted_in')
    const allSelected = optedInContacts.every((c) => selectedContactIds.includes(c.id))

    if (allSelected) {
      setSelectedContactIds([])
    } else {
      setSelectedContactIds(optedInContacts.map((c) => c.id))
    }
  }

  // Get selected contacts
  const selectedContacts = contacts.filter((c) => selectedContactIds.includes(c.id))

  // Send broadcast
  const handleSendBroadcast = async () => {
    if (selectedContactIds.length === 0 || !broadcastTemplate) return

    setIsSending(true)
    try {
      const response = await apiClient.post('/whatsapp/messages/broadcast', {
        contact_ids: selectedContactIds,
        template_name: broadcastTemplate,
        template_variables: {},
      })

      const result = response.data?.data
      alert(`Broadcast sent! ${result?.messages_queued || 0} messages queued.`)

      // Refresh data
      await fetchData()

      // Reset state
      setShowBroadcastModal(false)
      setSelectedContactIds([])
      setBroadcastTemplate('')
    } catch (err: any) {
      console.error('Failed to send broadcast:', err)
      alert(err.response?.data?.detail || 'Failed to send broadcast')
    } finally {
      setIsSending(false)
    }
  }

  // Validate phone number format
  const validatePhoneNumber = (phone: string): boolean => {
    // Basic validation: starts with + and has 10-15 digits
    const phoneRegex = /^\+?[1-9]\d{9,14}$/
    return phoneRegex.test(phone.replace(/[\s-]/g, ''))
  }

  // Parse CSV content
  const parseCSV = useCallback((content: string): CSVContact[] => {
    const lines = content.trim().split('\n')
    if (lines.length < 2) {
      setCsvError('CSV file must have a header row and at least one data row')
      return []
    }

    // Parse header
    const header = lines[0].toLowerCase().split(',').map(h => h.trim().replace(/"/g, ''))
    const phoneIndex = header.findIndex(h => h.includes('phone') || h.includes('number') || h.includes('mobile'))
    const countryIndex = header.findIndex(h => h.includes('country') || h.includes('code'))
    const nameIndex = header.findIndex(h => h.includes('name') || h.includes('display'))

    if (phoneIndex === -1) {
      setCsvError('CSV must have a column with "phone" or "number" in the header')
      return []
    }

    // Parse data rows
    const contacts: CSVContact[] = []
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue

      // Handle CSV with quotes
      const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))

      const phone = values[phoneIndex]?.trim() || ''
      const country = countryIndex !== -1 ? values[countryIndex]?.trim().toUpperCase() : ''
      const name = nameIndex !== -1 ? values[nameIndex]?.trim() : ''

      const isValid = validatePhoneNumber(phone)

      contacts.push({
        phone_number: phone.startsWith('+') ? phone : `+${phone}`,
        country_code: country || 'US',
        display_name: name,
        isValid,
        error: isValid ? undefined : 'Invalid phone number format'
      })
    }

    return contacts
  }, [])

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    setCsvError('')

    if (!file.name.endsWith('.csv')) {
      setCsvError('Please upload a CSV file')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setCsvError('File size must be less than 5MB')
      return
    }

    setCsvFileName(file.name)

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      const parsed = parseCSV(content)
      setCsvContacts(parsed)
    }
    reader.onerror = () => {
      setCsvError('Failed to read file')
    }
    reader.readAsText(file)
  }, [parseCSV])

  // Handle drag events
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  // Handle single contact submission
  const handleAddSingleContact = async () => {
    if (!newContactPhone || !newContactCountry) return

    setIsImporting(true)
    try {
      await apiClient.post('/whatsapp/contacts', {
        phone_number: newContactPhone.startsWith('+') ? newContactPhone : `+${newContactPhone}`,
        country_code: newContactCountry.toUpperCase(),
        display_name: newContactName || undefined,
        opt_in_method: 'web_form',
      })

      // Refresh contacts
      await fetchData()
      resetContactModal()
    } catch (err: any) {
      console.error('Failed to add contact:', err)
      alert(err.response?.data?.detail || 'Failed to add contact')
    } finally {
      setIsImporting(false)
    }
  }

  // Handle CSV import
  const handleImportCSV = async () => {
    const validContacts = csvContacts.filter(c => c.isValid)
    if (validContacts.length === 0) return

    setIsImporting(true)

    try {
      // Use bulk import endpoint
      const response = await apiClient.post('/whatsapp/contacts/bulk', {
        contacts: validContacts.map(contact => ({
          phone_number: contact.phone_number,
          country_code: contact.country_code,
          display_name: contact.display_name || undefined,
          opt_in_method: 'csv_import',
        })),
      })

      const result = response.data.data
      alert(`Imported ${result.success} contacts. ${result.failed > 0 ? `${result.failed} failed.` : ''}`)

      // Refresh contacts
      await fetchData()
      resetContactModal()
    } catch (err: any) {
      console.error('Failed to import contacts:', err)
      alert('Failed to import contacts: ' + (err.response?.data?.detail || err.message))
    } finally {
      setIsImporting(false)
    }
  }

  // Reset contact modal state
  const resetContactModal = () => {
    setShowNewContactModal(false)
    setAddContactTab('single')
    setCsvContacts([])
    setCsvFileName('')
    setCsvError('')
    setNewContactPhone('')
    setNewContactCountry('')
    setNewContactName('')
  }

  // Download sample CSV
  const downloadSampleCSV = () => {
    const sampleContent = `phone_number,country_code,display_name
+1234567890,US,John Smith
+9876543210,UK,Jane Doe
+1122334455,DE,Hans Mueller
+5544332211,BR,Maria Silva`

    const blob = new Blob([sampleContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'contacts_template.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Remove a contact from CSV preview
  const removeCSVContact = (index: number) => {
    setCsvContacts(prev => prev.filter((_, i) => i !== index))
  }

  const getOptInBadge = (status: OptInStatus) => {
    const styles = {
      opted_in: 'bg-green-500/10 text-green-500',
      pending: 'bg-amber-500/10 text-amber-500',
      opted_out: 'bg-red-500/10 text-red-500',
    }
    const labels = {
      opted_in: 'Opted In',
      pending: 'Pending',
      opted_out: 'Opted Out',
    }
    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium', styles[status])}>
        {labels[status]}
      </span>
    )
  }

  const getMessageStatusBadge = (status: MessageStatus) => {
    const config = {
      pending: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-500/10' },
      sent: { icon: Send, color: 'text-blue-500', bg: 'bg-blue-500/10' },
      delivered: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' },
      read: { icon: Eye, color: 'text-purple-500', bg: 'bg-purple-500/10' },
      failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
    }
    const { icon: Icon, color, bg } = config[status]
    return (
      <span className={cn('flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium', bg, color)}>
        <Icon className="w-3 h-3" />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getTemplateStatusBadge = (status: TemplateStatus) => {
    const styles = {
      approved: 'bg-green-500/10 text-green-500',
      pending: 'bg-amber-500/10 text-amber-500',
      rejected: 'bg-red-500/10 text-red-500',
      paused: 'bg-gray-500/10 text-gray-500',
    }
    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium', styles[status])}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getCategoryBadge = (category: string) => {
    const styles: Record<string, string> = {
      MARKETING: 'bg-purple-500/10 text-purple-500',
      UTILITY: 'bg-blue-500/10 text-blue-500',
      AUTHENTICATION: 'bg-amber-500/10 text-amber-500',
    }
    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium', styles[category] || 'bg-gray-500/10 text-gray-500')}>
        {category}
      </span>
    )
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const filteredContacts = contacts.filter((contact) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (
        !contact.phone_number.toLowerCase().includes(query) &&
        !contact.display_name?.toLowerCase().includes(query)
      ) {
        return false
      }
    }
    if (statusFilter !== 'all' && contact.opt_in_status !== statusFilter) {
      return false
    }
    return true
  })

  const filteredTemplates = templates.filter((template) => {
    if (searchQuery && !template.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (statusFilter !== 'all' && template.status !== statusFilter) {
      return false
    }
    return true
  })

  const filteredMessages = messages.filter((message) => {
    if (statusFilter !== 'all' && message.status !== statusFilter) {
      return false
    }
    return true
  })

  const getContactName = (contactId: number) => {
    const contact = contacts.find((c) => c.id === contactId)
    return contact?.display_name || contact?.phone_number || 'Unknown'
  }

  const stats = {
    totalContacts: contacts.length,
    optedIn: contacts.filter((c) => c.opt_in_status === 'opted_in').length,
    totalMessages: messages.length,
    delivered: messages.filter((m) => m.status === 'delivered' || m.status === 'read').length,
  }

  const optedInFilteredContacts = filteredContacts.filter((c) => c.opt_in_status === 'opted_in')
  const allOptedInSelected = optedInFilteredContacts.length > 0 &&
    optedInFilteredContacts.every((c) => selectedContactIds.includes(c.id))

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-green-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Loading WhatsApp data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 dark:text-red-400">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MessageCircle className="w-7 h-7 text-green-600" />
            WhatsApp Broadcast
          </h1>
          <p className="text-muted-foreground">Manage your contacts and send broadcast messages</p>
        </div>

        <div className="flex gap-2">
          {selectedContactIds.length > 0 && (
            <button
              onClick={() => setShowBroadcastModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors"
            >
              <Radio className="w-4 h-4" />
              <span>Broadcast ({selectedContactIds.length})</span>
            </button>
          )}
          <button
            onClick={() => setShowNewContactModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add Contact</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Users className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.totalContacts}</p>
              <p className="text-xs text-muted-foreground">My Contacts</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10">
              <UserCheck className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.optedIn}</p>
              <p className="text-xs text-muted-foreground">Can Receive</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10">
              <MessageCircle className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.totalMessages}</p>
              <p className="text-xs text-muted-foreground">Messages Sent</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <CheckCircle className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {stats.totalMessages > 0 ? Math.round((stats.delivered / stats.totalMessages) * 100) : 0}%
              </p>
              <p className="text-xs text-muted-foreground">Delivery Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Selection Info Bar */}
      {selectedContactIds.length > 0 && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-green-500/10 border border-green-500/20">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <span className="font-medium text-green-700">
              {selectedContactIds.length} contact{selectedContactIds.length > 1 ? 's' : ''} selected
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedContactIds([])}
              className="px-3 py-1 text-sm rounded-md hover:bg-green-500/20 transition-colors"
            >
              Clear Selection
            </button>
            <button
              onClick={() => setShowBroadcastModal(true)}
              className="flex items-center gap-1 px-3 py-1 text-sm rounded-md bg-green-600 text-white hover:bg-green-700 transition-colors"
            >
              <Send className="w-4 h-4" />
              Send Broadcast
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {[
            { id: 'inbox', label: 'Inbox', icon: Inbox, badge: conversations.reduce((acc, c) => acc + c.unreadCount, 0) },
            { id: 'contacts', label: 'My Contacts', icon: Users },
            { id: 'templates', label: 'Templates', icon: FileText },
            { id: 'messages', label: 'Message History', icon: MessageCircle },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as TabType)
                setSearchQuery('')
                setStatusFilter('all')
                setSelectedConversation(null)
              }}
              className={cn(
                'flex items-center gap-2 px-4 py-3 border-b-2 transition-colors relative',
                activeTab === tab.id
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.badge && tab.badge > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters - Hide when viewing a conversation */}
      {!(activeTab === 'inbox' && selectedConversation) && (
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={
              activeTab === 'inbox'
                ? 'Search conversations...'
                : activeTab === 'contacts'
                ? 'Search your contacts...'
                : activeTab === 'templates'
                ? 'Search templates...'
                : 'Search messages...'
            }
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
        >
          <option value="all">All Statuses</option>
          {activeTab === 'inbox' && (
            <>
              <option value="unread">Unread</option>
              <option value="active">Active</option>
            </>
          )}
          {activeTab === 'contacts' && (
            <>
              <option value="opted_in">Opted In</option>
              <option value="pending">Pending</option>
              <option value="opted_out">Opted Out</option>
            </>
          )}
          {activeTab === 'templates' && (
            <>
              <option value="approved">Approved</option>
              <option value="pending">Pending</option>
              <option value="rejected">Rejected</option>
            </>
          )}
          {activeTab === 'messages' && (
            <>
              <option value="sent">Sent</option>
              <option value="delivered">Delivered</option>
              <option value="read">Read</option>
              <option value="failed">Failed</option>
            </>
          )}
        </select>
      </div>
      )}

      {/* Content */}
      <div className="rounded-xl border bg-card overflow-hidden">
        {/* Inbox Tab */}
        {activeTab === 'inbox' && !selectedConversation && (
          <div className="divide-y">
            {conversations
              .filter((conv) => {
                if (searchQuery) {
                  const query = searchQuery.toLowerCase()
                  if (!conv.contact.display_name?.toLowerCase().includes(query) &&
                      !conv.contact.phone_number.toLowerCase().includes(query)) {
                    return false
                  }
                }
                if (statusFilter === 'unread' && conv.unreadCount === 0) return false
                if (statusFilter === 'active' && !conv.isActive) return false
                return true
              })
              .map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => {
                    setSelectedConversation(conv)
                    fetchContactMessages(conv.contact.id)
                  }}
                  className={cn(
                    'flex items-center gap-4 p-4 cursor-pointer hover:bg-muted/50 transition-colors',
                    conv.unreadCount > 0 && 'bg-green-500/5'
                  )}
                >
                  {/* Avatar */}
                  <div className="relative">
                    <div className={cn(
                      'w-12 h-12 rounded-full flex items-center justify-center',
                      conv.unreadCount > 0 ? 'bg-green-500 text-white' : 'bg-green-500/10'
                    )}>
                      <span className={cn('font-medium text-lg', conv.unreadCount === 0 && 'text-green-500')}>
                        {(conv.contact.display_name || conv.contact.phone_number).charAt(0).toUpperCase()}
                      </span>
                    </div>
                    {conv.isActive && (
                      <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-green-500 border-2 border-white" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className={cn('font-medium', conv.unreadCount > 0 && 'text-foreground')}>
                        {conv.contact.display_name || conv.contact.phone_number}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(conv.lastMessage.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <p className={cn(
                        'text-sm truncate max-w-[300px]',
                        conv.unreadCount > 0 ? 'text-foreground font-medium' : 'text-muted-foreground'
                      )}>
                        {conv.lastMessage.direction === 'outbound' && (
                          <span className="text-muted-foreground">You: </span>
                        )}
                        {conv.lastMessage.content || `Template: ${conv.lastMessage.template_name}`}
                      </p>
                      {conv.unreadCount > 0 && (
                        <span className="ml-2 w-5 h-5 rounded-full bg-green-500 text-white text-xs flex items-center justify-center">
                          {conv.unreadCount}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            {conversations.length === 0 && (
              <div className="p-12 text-center">
                <Inbox className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">No conversations yet</p>
                <p className="text-sm text-muted-foreground mt-1">Start by sending a message to a contact</p>
              </div>
            )}
          </div>
        )}

        {/* Inbox - Conversation View */}
        {activeTab === 'inbox' && selectedConversation && (
          <div className="flex flex-col h-[600px]">
            {/* Conversation Header */}
            <div className="flex items-center gap-4 p-4 border-b bg-muted/30">
              <button
                onClick={() => setSelectedConversation(null)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                <span className="text-green-500 font-medium">
                  {(selectedConversation.contact.display_name || selectedConversation.contact.phone_number).charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1">
                <p className="font-medium">{selectedConversation.contact.display_name || 'Unknown'}</p>
                <p className="text-sm text-muted-foreground">{selectedConversation.contact.phone_number}</p>
              </div>
              <div className="flex items-center gap-2">
                {selectedConversation.isActive && (
                  <span className="px-2 py-1 rounded-full bg-green-500/10 text-green-600 text-xs font-medium">
                    Active - 24h window
                  </span>
                )}
                <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                  <Phone className="w-5 h-5" />
                </button>
                <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                  <MoreHorizontal className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    'flex',
                    msg.direction === 'outbound' ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={cn(
                      'max-w-[70%] rounded-2xl px-4 py-2',
                      msg.direction === 'outbound'
                        ? 'bg-green-500 text-white rounded-br-md'
                        : 'bg-muted rounded-bl-md'
                    )}
                  >
                    {msg.template_name && (
                      <p className={cn(
                        'text-xs mb-1',
                        msg.direction === 'outbound' ? 'text-green-100' : 'text-muted-foreground'
                      )}>
                        Template: {msg.template_name}
                      </p>
                    )}
                    <p className="text-sm">{msg.content || `[${msg.template_name} template]`}</p>
                    <div className={cn(
                      'flex items-center gap-1 mt-1',
                      msg.direction === 'outbound' ? 'justify-end' : 'justify-start'
                    )}>
                      <span className={cn(
                        'text-xs',
                        msg.direction === 'outbound' ? 'text-green-100' : 'text-muted-foreground'
                      )}>
                        {new Date(msg.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {msg.direction === 'outbound' && (
                        <>
                          {msg.status === 'read' && <Eye className="w-3 h-3 text-green-100" />}
                          {msg.status === 'delivered' && <CheckCircle className="w-3 h-3 text-green-100" />}
                          {msg.status === 'sent' && <Send className="w-3 h-3 text-green-100" />}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Reply Input */}
            <div className="p-4 border-t bg-muted/30">
              {selectedConversation.isActive ? (
                <form
                  onSubmit={async (e) => {
                    e.preventDefault()
                    if (!replyText.trim() || isSending) return

                    setIsSending(true)
                    try {
                      await apiClient.post('/whatsapp/messages/send', {
                        contact_id: selectedConversation.contact.id,
                        message_type: 'text',
                        content: replyText.trim(),
                      })

                      // Add message to local state for immediate feedback
                      const newMessage: WhatsAppMessage = {
                        id: Date.now(),
                        contact_id: selectedConversation.contact.id,
                        direction: 'outbound',
                        message_type: 'text',
                        status: 'sent',
                        content: replyText.trim(),
                        template_name: null,
                        sent_at: new Date().toISOString(),
                        delivered_at: null,
                        read_at: null,
                        created_at: new Date().toISOString(),
                      }
                      setChatMessages(prev => [...prev, newMessage])
                      setReplyText('')
                    } catch (err: any) {
                      console.error('Failed to send message:', err)
                      alert(err.response?.data?.detail || 'Failed to send message')
                    } finally {
                      setIsSending(false)
                    }
                  }}
                  className="flex items-center gap-2"
                >
                  <button type="button" className="p-2 rounded-lg hover:bg-muted transition-colors">
                    <Paperclip className="w-5 h-5 text-muted-foreground" />
                  </button>
                  <button type="button" className="p-2 rounded-lg hover:bg-muted transition-colors">
                    <Image className="w-5 h-5 text-muted-foreground" />
                  </button>
                  <input
                    type="text"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 px-4 py-2 rounded-full border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
                    disabled={isSending}
                  />
                  <button type="button" className="p-2 rounded-lg hover:bg-muted transition-colors">
                    <Smile className="w-5 h-5 text-muted-foreground" />
                  </button>
                  <button
                    type="submit"
                    disabled={!replyText.trim() || isSending}
                    className="p-2 rounded-lg bg-green-500 text-white hover:bg-green-600 transition-colors disabled:opacity-50"
                  >
                    {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                  </button>
                </form>
              ) : (
                <div className="text-center py-4">
                  <p className="text-sm text-muted-foreground mb-2">
                    24-hour conversation window has expired
                  </p>
                  <button
                    onClick={() => {
                      setSelectedContactIds([selectedConversation.contact.id])
                      setShowBroadcastModal(true)
                    }}
                    className="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors text-sm"
                  >
                    Send Template Message
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Contacts Tab */}
        {activeTab === 'contacts' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="p-4 text-left">
                    <input
                      type="checkbox"
                      checked={allOptedInSelected && optedInFilteredContacts.length > 0}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
                      title="Select all opted-in contacts"
                    />
                  </th>
                  <th className="p-4 text-left text-sm font-medium">Contact</th>
                  <th className="p-4 text-left text-sm font-medium">Phone</th>
                  <th className="p-4 text-left text-sm font-medium">Status</th>
                  <th className="p-4 text-center text-sm font-medium">Verified</th>
                  <th className="p-4 text-right text-sm font-medium">Messages</th>
                  <th className="p-4 text-left text-sm font-medium">Last Message</th>
                  <th className="p-4 text-right text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredContacts.map((contact) => {
                  const isSelected = selectedContactIds.includes(contact.id)
                  const canSelect = contact.opt_in_status === 'opted_in'

                  return (
                    <tr
                      key={contact.id}
                      className={cn(
                        'hover:bg-muted/30 transition-colors',
                        isSelected && 'bg-green-500/5'
                      )}
                    >
                      <td className="p-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleContactSelection(contact.id)}
                          disabled={!canSelect}
                          className={cn(
                            'w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500',
                            !canSelect && 'opacity-30 cursor-not-allowed'
                          )}
                          title={!canSelect ? 'Contact must be opted-in to receive messages' : ''}
                        />
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            'w-10 h-10 rounded-full flex items-center justify-center',
                            isSelected ? 'bg-green-500 text-white' : 'bg-green-500/10'
                          )}>
                            <span className={cn('font-medium', !isSelected && 'text-green-500')}>
                              {(contact.display_name || contact.phone_number).charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium">{contact.display_name || 'Unknown'}</p>
                            <p className="text-xs text-muted-foreground">{contact.country_code}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4 font-mono text-sm">{contact.phone_number}</td>
                      <td className="p-4">{getOptInBadge(contact.opt_in_status)}</td>
                      <td className="p-4 text-center">
                        {contact.is_verified ? (
                          <CheckCircle className="w-5 h-5 text-green-500 mx-auto" />
                        ) : (
                          <XCircle className="w-5 h-5 text-gray-400 mx-auto" />
                        )}
                      </td>
                      <td className="p-4 text-right font-medium">{contact.message_count}</td>
                      <td className="p-4 text-sm text-muted-foreground">
                        {formatDate(contact.last_message_at)}
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {canSelect && (
                            <button
                              onClick={() => {
                                setSelectedContactIds([contact.id])
                                setShowBroadcastModal(true)
                              }}
                              className="p-2 rounded-lg hover:bg-muted transition-colors"
                              title="Send Message"
                            >
                              <Send className="w-4 h-4" />
                            </button>
                          )}
                          <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                            <MoreHorizontal className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {filteredContacts.length === 0 && (
              <div className="p-12 text-center">
                <Users className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">No contacts found</p>
                <button
                  onClick={() => setShowNewContactModal(true)}
                  className="mt-3 text-green-600 hover:underline"
                >
                  Add your first contact
                </button>
              </div>
            )}
          </div>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="p-4 text-left text-sm font-medium">Template Name</th>
                  <th className="p-4 text-left text-sm font-medium">Category</th>
                  <th className="p-4 text-left text-sm font-medium">Status</th>
                  <th className="p-4 text-left text-sm font-medium">Body</th>
                  <th className="p-4 text-right text-sm font-medium">Usage</th>
                  <th className="p-4 text-left text-sm font-medium">Created</th>
                  <th className="p-4 text-right text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredTemplates.map((template) => (
                  <tr key={template.id} className="hover:bg-muted/30 transition-colors">
                    <td className="p-4">
                      <div>
                        <p className="font-medium font-mono">{template.name}</p>
                        <p className="text-xs text-muted-foreground">{template.language.toUpperCase()}</p>
                      </div>
                    </td>
                    <td className="p-4">{getCategoryBadge(template.category)}</td>
                    <td className="p-4">{getTemplateStatusBadge(template.status)}</td>
                    <td className="p-4 max-w-xs">
                      <p className="text-sm truncate" title={template.body_text}>
                        {template.body_text}
                      </p>
                    </td>
                    <td className="p-4 text-right font-medium">{template.usage_count.toLocaleString()}</td>
                    <td className="p-4 text-sm text-muted-foreground">{formatDate(template.created_at)}</td>
                    <td className="p-4 text-right">
                      <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredTemplates.length === 0 && (
              <div className="p-12 text-center">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">No templates found</p>
              </div>
            )}
          </div>
        )}

        {/* Messages Tab */}
        {activeTab === 'messages' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="p-4 text-left text-sm font-medium">Contact</th>
                  <th className="p-4 text-left text-sm font-medium">Direction</th>
                  <th className="p-4 text-left text-sm font-medium">Type</th>
                  <th className="p-4 text-left text-sm font-medium">Content</th>
                  <th className="p-4 text-left text-sm font-medium">Status</th>
                  <th className="p-4 text-left text-sm font-medium">Sent At</th>
                  <th className="p-4 text-right text-sm font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredMessages.map((message) => (
                  <tr key={message.id} className="hover:bg-muted/30 transition-colors">
                    <td className="p-4 font-medium">{getContactName(message.contact_id)}</td>
                    <td className="p-4">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs font-medium',
                          message.direction === 'outbound'
                            ? 'bg-blue-500/10 text-blue-500'
                            : 'bg-green-500/10 text-green-500'
                        )}
                      >
                        {message.direction === 'outbound' ? 'Sent' : 'Received'}
                      </span>
                    </td>
                    <td className="p-4 text-sm capitalize">{message.message_type}</td>
                    <td className="p-4 max-w-xs">
                      <p className="text-sm truncate">
                        {message.content || (message.template_name ? `Template: ${message.template_name}` : '-')}
                      </p>
                    </td>
                    <td className="p-4">{getMessageStatusBadge(message.status)}</td>
                    <td className="p-4 text-sm text-muted-foreground">{formatDate(message.sent_at || message.created_at)}</td>
                    <td className="p-4 text-right">
                      <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredMessages.length === 0 && (
              <div className="p-12 text-center">
                <MessageCircle className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">No messages found</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* New Contact Modal - Enhanced with CSV Upload */}
      {showNewContactModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-xl border shadow-lg w-full max-w-xl p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Add Contacts</h2>
              <button
                onClick={resetContactModal}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 p-1 rounded-lg bg-muted mb-6">
              <button
                onClick={() => setAddContactTab('single')}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                  addContactTab === 'single'
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <UserCheck className="w-4 h-4" />
                Single Contact
              </button>
              <button
                onClick={() => setAddContactTab('csv')}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                  addContactTab === 'csv'
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <FileSpreadsheet className="w-4 h-4" />
                Import CSV
              </button>
            </div>

            {/* Single Contact Form */}
            {addContactTab === 'single' && (
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  handleAddSingleContact()
                }}
                className="space-y-4"
              >
                <div>
                  <label className="block text-sm font-medium mb-1">Phone Number *</label>
                  <input
                    type="tel"
                    placeholder="+1234567890"
                    value={newContactPhone}
                    onChange={(e) => setNewContactPhone(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">Include country code (e.g., +1 for US)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Country Code *</label>
                  <input
                    type="text"
                    placeholder="US"
                    value={newContactCountry}
                    onChange={(e) => setNewContactCountry(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Display Name</label>
                  <input
                    type="text"
                    placeholder="John Smith"
                    value={newContactName}
                    onChange={(e) => setNewContactName(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
                  />
                </div>
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={resetContactModal}
                    className="flex-1 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!newContactPhone || !newContactCountry}
                    className="flex-1 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Add Contact
                  </button>
                </div>
              </form>
            )}

            {/* CSV Upload Form */}
            {addContactTab === 'csv' && (
              <div className="space-y-4">
                {/* Download Template */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-dashed">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">CSV Template</p>
                      <p className="text-xs text-muted-foreground">Download a sample template to get started</p>
                    </div>
                  </div>
                  <button
                    onClick={downloadSampleCSV}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-background border hover:bg-muted transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>

                {/* Drop Zone */}
                {csvContacts.length === 0 && (
                  <div
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={cn(
                      'relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all',
                      isDragging
                        ? 'border-green-500 bg-green-500/5'
                        : 'border-muted-foreground/25 hover:border-green-500/50 hover:bg-muted/50'
                    )}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleFileSelect(file)
                      }}
                      className="hidden"
                    />
                    <Upload className={cn(
                      'w-10 h-10 mx-auto mb-3',
                      isDragging ? 'text-green-500' : 'text-muted-foreground'
                    )} />
                    <p className="text-sm font-medium mb-1">
                      {isDragging ? 'Drop your file here' : 'Drag & drop your CSV file here'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      or click to browse (max 5MB)
                    </p>
                  </div>
                )}

                {/* Error Message */}
                {csvError && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-600">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <p className="text-sm">{csvError}</p>
                  </div>
                )}

                {/* CSV Preview */}
                {csvContacts.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className="w-4 h-4 text-green-600" />
                        <span className="text-sm font-medium">{csvFileName}</span>
                      </div>
                      <button
                        onClick={() => {
                          setCsvContacts([])
                          setCsvFileName('')
                          setCsvError('')
                        }}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Clear
                      </button>
                    </div>

                    {/* Summary */}
                    <div className="flex gap-4 p-3 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span className="text-sm">
                          <strong>{csvContacts.filter(c => c.isValid).length}</strong> valid
                        </span>
                      </div>
                      {csvContacts.filter(c => !c.isValid).length > 0 && (
                        <div className="flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-500" />
                          <span className="text-sm">
                            <strong>{csvContacts.filter(c => !c.isValid).length}</strong> invalid
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Contact List */}
                    <div className="max-h-48 overflow-y-auto rounded-lg border divide-y">
                      {csvContacts.map((contact, index) => (
                        <div
                          key={index}
                          className={cn(
                            'flex items-center justify-between p-3',
                            !contact.isValid && 'bg-red-500/5'
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              'w-8 h-8 rounded-full flex items-center justify-center',
                              contact.isValid ? 'bg-green-500/10' : 'bg-red-500/10'
                            )}>
                              {contact.isValid ? (
                                <CheckCircle className="w-4 h-4 text-green-500" />
                              ) : (
                                <AlertCircle className="w-4 h-4 text-red-500" />
                              )}
                            </div>
                            <div>
                              <p className="text-sm font-medium">
                                {contact.display_name || 'No name'}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {contact.phone_number} • {contact.country_code}
                              </p>
                              {contact.error && (
                                <p className="text-xs text-red-500">{contact.error}</p>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => removeCSVContact(index)}
                            className="p-1.5 rounded-md hover:bg-muted transition-colors"
                          >
                            <X className="w-4 h-4 text-muted-foreground" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={resetContactModal}
                    className="flex-1 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleImportCSV}
                    disabled={csvContacts.filter(c => c.isValid).length === 0 || isImporting}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isImporting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Importing...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4" />
                        Import {csvContacts.filter(c => c.isValid).length} Contacts
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Broadcast Modal */}
      {showBroadcastModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-xl border shadow-lg w-full max-w-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Radio className="w-6 h-6 text-green-600" />
              <h2 className="text-xl font-bold">Send Broadcast</h2>
            </div>

            <div className="mb-4 p-3 rounded-lg bg-muted/50">
              <p className="text-sm text-muted-foreground mb-2">Sending to {selectedContactIds.length} contact{selectedContactIds.length > 1 ? 's' : ''}:</p>
              <div className="flex flex-wrap gap-2">
                {selectedContacts.slice(0, 5).map((contact) => (
                  <span key={contact.id} className="px-2 py-1 rounded-full bg-green-500/10 text-green-600 text-xs font-medium">
                    {contact.display_name || contact.phone_number}
                  </span>
                ))}
                {selectedContactIds.length > 5 && (
                  <span className="px-2 py-1 rounded-full bg-gray-500/10 text-gray-500 text-xs font-medium">
                    +{selectedContactIds.length - 5} more
                  </span>
                )}
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSendBroadcast()
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-sm font-medium mb-1">Select Template *</label>
                <select
                  value={broadcastTemplate}
                  onChange={(e) => setBroadcastTemplate(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-green-500/20"
                  required
                >
                  <option value="">Choose a template...</option>
                  {templates
                    .filter((t) => t.status === 'approved')
                    .map((t) => (
                      <option key={t.id} value={t.name}>
                        {t.name} ({t.category})
                      </option>
                    ))}
                </select>
              </div>

              {broadcastTemplate && (
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground mb-1">Preview:</p>
                  <p className="text-sm">
                    {templates.find((t) => t.name === broadcastTemplate)?.body_text}
                  </p>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowBroadcastModal(false)
                    setBroadcastTemplate('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!broadcastTemplate || isSending}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Send to {selectedContactIds.length} Contact{selectedContactIds.length > 1 ? 's' : ''}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default WhatsApp
