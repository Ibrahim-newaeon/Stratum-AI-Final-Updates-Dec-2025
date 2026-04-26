/**
 * Stratum AI - WhatsApp API
 *
 * WhatsApp Business API integration for contacts, templates, messages, and conversations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface WhatsAppContact {
  id: number
  phone_number: string
  country_code: string
  display_name?: string
  is_verified: boolean
  opt_in_status: string
  wa_id?: string
  profile_name?: string
  message_count: number
  last_message_at?: string
  created_at: string
}

export interface WhatsAppContactCreate {
  phone_number: string
  country_code: string
  display_name?: string
  opt_in_method?: string
}

export interface WhatsAppContactUpdate {
  display_name?: string
  country_code?: string
}

export interface WhatsAppContactListResponse {
  items: WhatsAppContact[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface WhatsAppTemplate {
  id: number
  name: string
  language: string
  category: string
  body_text: string
  status: string
  usage_count: number
  created_at: string
}

export interface WhatsAppTemplateCreate {
  name: string
  language?: string
  category: string
  header_type?: string
  header_content?: string
  body_text: string
  footer_text?: string
  header_variables?: string[]
  body_variables?: string[]
  buttons?: Record<string, unknown>[]
}

export interface WhatsAppTemplateListResponse {
  items: WhatsAppTemplate[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface WhatsAppMessage {
  id: number
  contact_id: number
  direction: string
  message_type: string
  status: string
  content?: string
  template_name?: string
  sent_at?: string
  delivered_at?: string
  read_at?: string
  created_at: string
}

export interface WhatsAppMessageSend {
  contact_id: number
  message_type: string
  template_name?: string
  template_variables?: Record<string, unknown>
  content?: string
  media_url?: string
  scheduled_at?: string
}

export interface WhatsAppMessageListResponse {
  items: WhatsAppMessage[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface WhatsAppConversation {
  id: number
  contact_id: number
  origin_type: string
  pricing_category?: string
  started_at: string
  expires_at: string
  message_count: number
  is_active: boolean
}

export interface WhatsAppConversationListResponse {
  items: WhatsAppConversation[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ContactFilters {
  page?: number
  page_size?: number
  opt_in_status?: string
  search?: string
}

export interface TemplateFilters {
  page?: number
  page_size?: number
  status?: string
  category?: string
}

export interface MessageFilters {
  page?: number
  page_size?: number
  contact_id?: number
  status?: string
}

export interface ConversationFilters {
  page?: number
  page_size?: number
  contact_id?: number
  active_only?: boolean
}

// API Functions
export const whatsappApi = {
  getContacts: async (filters: ContactFilters = {}): Promise<WhatsAppContactListResponse> => {
    const response = await apiClient.get<ApiResponse<WhatsAppContactListResponse>>('/whatsapp/contacts', {
      params: filters,
    })
    return response.data.data
  },

  createContact: async (data: WhatsAppContactCreate): Promise<WhatsAppContact> => {
    const response = await apiClient.post<ApiResponse<WhatsAppContact>>('/whatsapp/contacts', data)
    return response.data.data
  },

  getContact: async (id: number): Promise<WhatsAppContact> => {
    const response = await apiClient.get<ApiResponse<WhatsAppContact>>(`/whatsapp/contacts/${id}`)
    return response.data.data
  },

  updateContact: async (id: number, data: WhatsAppContactUpdate): Promise<WhatsAppContact> => {
    const response = await apiClient.patch<ApiResponse<WhatsAppContact>>(`/whatsapp/contacts/${id}`, data)
    return response.data.data
  },

  deleteContact: async (id: number): Promise<void> => {
    await apiClient.delete(`/whatsapp/contacts/${id}`)
  },

  getTemplates: async (filters: TemplateFilters = {}): Promise<WhatsAppTemplateListResponse> => {
    const response = await apiClient.get<ApiResponse<WhatsAppTemplateListResponse>>('/whatsapp/templates', {
      params: filters,
    })
    return response.data.data
  },

  createTemplate: async (data: WhatsAppTemplateCreate): Promise<WhatsAppTemplate> => {
    const response = await apiClient.post<ApiResponse<WhatsAppTemplate>>('/whatsapp/templates', data)
    return response.data.data
  },

  getMessages: async (filters: MessageFilters = {}): Promise<WhatsAppMessageListResponse> => {
    const response = await apiClient.get<ApiResponse<WhatsAppMessageListResponse>>('/whatsapp/messages', {
      params: filters,
    })
    return response.data.data
  },

  sendMessage: async (data: WhatsAppMessageSend): Promise<WhatsAppMessage> => {
    const response = await apiClient.post<ApiResponse<WhatsAppMessage>>('/whatsapp/messages/send', data)
    return response.data.data
  },

  getConversations: async (filters: ConversationFilters = {}): Promise<WhatsAppConversationListResponse> => {
    const response = await apiClient.get<ApiResponse<WhatsAppConversationListResponse>>(
      '/whatsapp/conversations',
      { params: filters }
    )
    return response.data.data
  },
}

// React Query Hooks
export function useWhatsAppContacts(filters: ContactFilters = {}) {
  return useQuery({
    queryKey: ['whatsapp', 'contacts', filters],
    queryFn: () => whatsappApi.getContacts(filters),
    staleTime: 30 * 1000,
  })
}

export function useCreateWhatsAppContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: whatsappApi.createContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'contacts'] })
    },
  })
}

export function useWhatsAppContact(id: number) {
  return useQuery({
    queryKey: ['whatsapp', 'contacts', id],
    queryFn: () => whatsappApi.getContact(id),
    enabled: !!id,
  })
}

export function useUpdateWhatsAppContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: WhatsAppContactUpdate }) => whatsappApi.updateContact(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'contacts'] })
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'contacts', variables.id] })
    },
  })
}

export function useDeleteWhatsAppContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: whatsappApi.deleteContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'contacts'] })
    },
  })
}

export function useWhatsAppTemplates(filters: TemplateFilters = {}) {
  return useQuery({
    queryKey: ['whatsapp', 'templates', filters],
    queryFn: () => whatsappApi.getTemplates(filters),
    staleTime: 30 * 1000,
  })
}

export function useCreateWhatsAppTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: whatsappApi.createTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'templates'] })
    },
  })
}

export function useWhatsAppMessages(filters: MessageFilters = {}) {
  return useQuery({
    queryKey: ['whatsapp', 'messages', filters],
    queryFn: () => whatsappApi.getMessages(filters),
    staleTime: 30 * 1000,
  })
}

export function useSendWhatsAppMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: whatsappApi.sendMessage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'messages'] })
      queryClient.invalidateQueries({ queryKey: ['whatsapp', 'conversations'] })
    },
  })
}

export function useWhatsAppConversations(filters: ConversationFilters = {}) {
  return useQuery({
    queryKey: ['whatsapp', 'conversations', filters],
    queryFn: () => whatsappApi.getConversations(filters),
    staleTime: 30 * 1000,
  })
}
