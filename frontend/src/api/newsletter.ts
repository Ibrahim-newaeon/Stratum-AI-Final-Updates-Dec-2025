/**
 * Stratum AI - Newsletter / Email Campaign API
 *
 * React Query hooks for campaign management, templates,
 * subscriber management, and analytics.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse } from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type CampaignStatus = 'draft' | 'scheduled' | 'sending' | 'sent' | 'paused' | 'cancelled';
export type TemplateCategory = 'promotional' | 'transactional' | 'update' | 'announcement';

export interface NewsletterTemplate {
  id: number;
  name: string;
  subject: string;
  preheader_text: string | null;
  content_html: string | null;
  content_json: Record<string, unknown> | null;
  category: TemplateCategory;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NewsletterCampaign {
  id: number;
  name: string;
  subject: string;
  preheader_text: string | null;
  content_html: string | null;
  content_json: Record<string, unknown> | null;
  template_id: number | null;
  status: CampaignStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  completed_at: string | null;
  from_name: string | null;
  from_email: string | null;
  reply_to_email: string | null;
  audience_filters: AudienceFilters | null;
  total_recipients: number;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_unsubscribed: number;
  created_at: string;
  updated_at: string;
}

export interface AudienceFilters {
  status?: string[];
  min_lead_score?: number;
  platforms?: string[];
}

export interface CampaignListResponse {
  campaigns: NewsletterCampaign[];
  total: number;
}

export interface CampaignFilters {
  status?: CampaignStatus;
  limit?: number;
  offset?: number;
}

export interface NewsletterSubscriber {
  id: number;
  email: string;
  full_name: string | null;
  company_name: string | null;
  status: string;
  attributed_platform: string | null;
  lead_score: number;
  subscribed_to_newsletter: boolean;
  unsubscribed_at: string | null;
  last_email_sent_at: string | null;
  last_email_opened_at: string | null;
  email_send_count: number;
  email_open_count: number;
  created_at: string;
}

export interface SubscriberFilters {
  subscribed?: boolean;
  platform?: string;
  min_score?: number;
  limit?: number;
  offset?: number;
}

export interface SubscriberStats {
  total: number;
  active: number;
  unsubscribed: number;
}

export interface CampaignAnalytics {
  campaign: NewsletterCampaign;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  unsubscribe_rate: number;
  events: Array<{
    id: number;
    event_type: string;
    subscriber_id: number;
    metadata: Record<string, unknown> | null;
    created_at: string;
  }>;
}

export interface TemplateCreate {
  name: string;
  subject?: string;
  preheader_text?: string;
  content_html?: string;
  content_json?: Record<string, unknown>;
  category?: TemplateCategory;
}

export interface TemplateUpdate {
  name?: string;
  subject?: string;
  preheader_text?: string;
  content_html?: string;
  content_json?: Record<string, unknown>;
  category?: TemplateCategory;
  is_active?: boolean;
}

export interface CampaignCreate {
  name: string;
  subject: string;
  preheader_text?: string;
  content_html?: string;
  content_json?: Record<string, unknown>;
  template_id?: number;
  from_name?: string;
  from_email?: string;
  reply_to_email?: string;
  audience_filters?: AudienceFilters;
}

export interface CampaignUpdate {
  name?: string;
  subject?: string;
  preheader_text?: string;
  content_html?: string;
  content_json?: Record<string, unknown>;
  template_id?: number;
  from_name?: string;
  from_email?: string;
  reply_to_email?: string;
  audience_filters?: AudienceFilters;
}

// ---------------------------------------------------------------------------
// Query Keys
// ---------------------------------------------------------------------------
export const newsletterKeys = {
  all: ['newsletter'] as const,
  campaigns: () => [...newsletterKeys.all, 'campaigns'] as const,
  campaignsList: (filters: CampaignFilters) => [...newsletterKeys.campaigns(), 'list', filters] as const,
  campaignDetail: (id: number) => [...newsletterKeys.campaigns(), 'detail', id] as const,
  campaignAnalytics: (id: number) => [...newsletterKeys.campaigns(), 'analytics', id] as const,
  templates: () => [...newsletterKeys.all, 'templates'] as const,
  subscribers: () => [...newsletterKeys.all, 'subscribers'] as const,
  subscribersList: (filters: SubscriberFilters) => [...newsletterKeys.subscribers(), 'list', filters] as const,
  subscriberStats: () => [...newsletterKeys.subscribers(), 'stats'] as const,
  audienceCount: (filters: AudienceFilters) => [...newsletterKeys.all, 'audienceCount', filters] as const,
};

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

// Campaigns
const fetchCampaigns = async (filters: CampaignFilters = {}): Promise<CampaignListResponse> => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.limit) params.append('limit', String(filters.limit));
  if (filters.offset) params.append('offset', String(filters.offset));

  const response = await apiClient.get<ApiResponse<CampaignListResponse>>(
    `/newsletter/campaigns?${params.toString()}`
  );
  return response.data.data;
};

const fetchCampaign = async (id: number): Promise<NewsletterCampaign> => {
  const response = await apiClient.get<ApiResponse<NewsletterCampaign>>(
    `/newsletter/campaigns/${id}`
  );
  return response.data.data;
};

const createCampaign = async (data: CampaignCreate): Promise<NewsletterCampaign> => {
  const response = await apiClient.post<ApiResponse<NewsletterCampaign>>(
    '/newsletter/campaigns',
    data
  );
  return response.data.data;
};

const updateCampaign = async ({
  id,
  data,
}: {
  id: number;
  data: CampaignUpdate;
}): Promise<NewsletterCampaign> => {
  const response = await apiClient.put<ApiResponse<NewsletterCampaign>>(
    `/newsletter/campaigns/${id}`,
    data
  );
  return response.data.data;
};

const deleteCampaign = async (id: number): Promise<void> => {
  await apiClient.delete(`/newsletter/campaigns/${id}`);
};

const duplicateCampaign = async (id: number): Promise<NewsletterCampaign> => {
  const response = await apiClient.post<ApiResponse<NewsletterCampaign>>(
    `/newsletter/campaigns/${id}/duplicate`
  );
  return response.data.data;
};

const sendCampaign = async (id: number): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<ApiResponse<{ success: boolean; message: string }>>(
    `/newsletter/campaigns/${id}/send`
  );
  return response.data.data;
};

const scheduleCampaign = async ({
  id,
  scheduled_at,
}: {
  id: number;
  scheduled_at: string;
}): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<ApiResponse<{ success: boolean; message: string }>>(
    `/newsletter/campaigns/${id}/schedule`,
    { scheduled_at }
  );
  return response.data.data;
};

const cancelCampaign = async (id: number): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<ApiResponse<{ success: boolean; message: string }>>(
    `/newsletter/campaigns/${id}/cancel`
  );
  return response.data.data;
};

const sendTestEmail = async ({
  id,
  emails,
}: {
  id: number;
  emails: string[];
}): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<ApiResponse<{ success: boolean; message: string }>>(
    `/newsletter/campaigns/${id}/send-test`,
    { emails }
  );
  return response.data.data;
};

const fetchCampaignAnalytics = async (id: number): Promise<CampaignAnalytics> => {
  const response = await apiClient.get<ApiResponse<CampaignAnalytics>>(
    `/newsletter/campaigns/${id}/analytics`
  );
  return response.data.data;
};

// Templates
const fetchTemplates = async (): Promise<NewsletterTemplate[]> => {
  const response = await apiClient.get<ApiResponse<NewsletterTemplate[]>>(
    '/newsletter/templates'
  );
  return response.data.data;
};

const createTemplate = async (data: TemplateCreate): Promise<NewsletterTemplate> => {
  const response = await apiClient.post<ApiResponse<NewsletterTemplate>>(
    '/newsletter/templates',
    data
  );
  return response.data.data;
};

const updateTemplate = async ({
  id,
  data,
}: {
  id: number;
  data: TemplateUpdate;
}): Promise<NewsletterTemplate> => {
  const response = await apiClient.put<ApiResponse<NewsletterTemplate>>(
    `/newsletter/templates/${id}`,
    data
  );
  return response.data.data;
};

const deleteTemplate = async (id: number): Promise<void> => {
  await apiClient.delete(`/newsletter/templates/${id}`);
};

// Subscribers
const fetchSubscribers = async (filters: SubscriberFilters = {}): Promise<NewsletterSubscriber[]> => {
  const params = new URLSearchParams();
  if (filters.subscribed !== undefined) params.append('subscribed', String(filters.subscribed));
  if (filters.platform) params.append('platform', filters.platform);
  if (filters.min_score !== undefined) params.append('min_score', String(filters.min_score));
  if (filters.limit) params.append('limit', String(filters.limit));
  if (filters.offset) params.append('offset', String(filters.offset));

  const response = await apiClient.get<ApiResponse<NewsletterSubscriber[]>>(
    `/newsletter/subscribers?${params.toString()}`
  );
  return response.data.data;
};

const fetchSubscriberStats = async (): Promise<SubscriberStats> => {
  const response = await apiClient.get<ApiResponse<SubscriberStats>>(
    '/newsletter/subscribers/stats'
  );
  return response.data.data;
};

const unsubscribeSubscriber = async (id: number): Promise<void> => {
  await apiClient.put(`/newsletter/subscribers/${id}/unsubscribe`);
};

const resubscribeSubscriber = async (id: number): Promise<void> => {
  await apiClient.put(`/newsletter/subscribers/${id}/resubscribe`);
};

const fetchAudienceCount = async (filters: AudienceFilters): Promise<number> => {
  const params = new URLSearchParams();
  if (filters.status?.length) params.append('status', filters.status.join(','));
  if (filters.min_lead_score !== undefined) params.append('min_lead_score', String(filters.min_lead_score));
  if (filters.platforms?.length) params.append('platform', filters.platforms.join(','));

  const response = await apiClient.get<ApiResponse<{ count: number }>>(
    `/newsletter/subscribers/count?${params.toString()}`
  );
  return response.data.data.count;
};

// ---------------------------------------------------------------------------
// React Query Hooks
// ---------------------------------------------------------------------------

// Campaigns
export function useCampaigns(filters: CampaignFilters = {}) {
  return useQuery({
    queryKey: newsletterKeys.campaignsList(filters),
    queryFn: () => fetchCampaigns(filters),
  });
}

export function useCampaign(id: number) {
  return useQuery({
    queryKey: newsletterKeys.campaignDetail(id),
    queryFn: () => fetchCampaign(id),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
    },
  });
}

export function useUpdateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateCampaign,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
      queryClient.setQueryData(newsletterKeys.campaignDetail(data.id), data);
    },
  });
}

export function useDeleteCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
    },
  });
}

export function useDuplicateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: duplicateCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
    },
  });
}

export function useSendCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: sendCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
    },
  });
}

export function useScheduleCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: scheduleCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
    },
  });
}

export function useCancelCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cancelCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.campaigns() });
    },
  });
}

export function useSendTestEmail() {
  return useMutation({
    mutationFn: sendTestEmail,
  });
}

export function useCampaignAnalytics(id: number) {
  return useQuery({
    queryKey: newsletterKeys.campaignAnalytics(id),
    queryFn: () => fetchCampaignAnalytics(id),
    enabled: !!id,
  });
}

// Templates
export function useTemplates() {
  return useQuery({
    queryKey: newsletterKeys.templates(),
    queryFn: fetchTemplates,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.templates() });
    },
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.templates() });
    },
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.templates() });
    },
  });
}

// Subscribers
export function useNewsletterSubscribers(filters: SubscriberFilters = {}) {
  return useQuery({
    queryKey: newsletterKeys.subscribersList(filters),
    queryFn: () => fetchSubscribers(filters),
  });
}

export function useSubscriberStats() {
  return useQuery({
    queryKey: newsletterKeys.subscriberStats(),
    queryFn: fetchSubscriberStats,
  });
}

export function useUnsubscribe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: unsubscribeSubscriber,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.subscribers() });
    },
  });
}

export function useResubscribe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resubscribeSubscriber,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsletterKeys.subscribers() });
    },
  });
}

export function useAudienceCount(filters: AudienceFilters) {
  return useQuery({
    queryKey: newsletterKeys.audienceCount(filters),
    queryFn: () => fetchAudienceCount(filters),
    enabled: Object.keys(filters).length > 0,
  });
}
