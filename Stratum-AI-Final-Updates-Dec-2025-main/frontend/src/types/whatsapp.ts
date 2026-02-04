// =============================================================================
// Stratum AI - WhatsApp Types
// =============================================================================

export type OptInStatus = 'pending' | 'opted_in' | 'opted_out';
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
export type MessageDirection = 'outbound' | 'inbound';
export type TemplateStatus = 'pending' | 'approved' | 'rejected' | 'paused';
export type TemplateCategory = 'MARKETING' | 'UTILITY' | 'AUTHENTICATION';

export interface WhatsAppContact {
  id: number;
  phone_number: string;
  country_code: string;
  display_name: string | null;
  is_verified: boolean;
  opt_in_status: OptInStatus;
  wa_id: string | null;
  profile_name: string | null;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
}

export interface WhatsAppTemplate {
  id: number;
  name: string;
  language: string;
  category: TemplateCategory;
  body_text: string;
  status: TemplateStatus;
  usage_count: number;
  created_at: string;
}

export interface WhatsAppMessage {
  id: number;
  contact_id: number;
  direction: MessageDirection;
  message_type: string;
  status: MessageStatus;
  content: string | null;
  template_name: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  created_at: string;
}

export interface WhatsAppConversation {
  id: number;
  contact_id: number;
  origin_type: string;
  pricing_category: string | null;
  started_at: string;
  expires_at: string;
  message_count: number;
  is_active: boolean;
}

// Request/Response types
export interface CreateContactRequest {
  phone_number: string;
  country_code: string;
  display_name?: string;
  opt_in_method?: string;
}

export interface CreateTemplateRequest {
  name: string;
  language: string;
  category: TemplateCategory;
  header_type?: string;
  header_content?: string;
  body_text: string;
  footer_text?: string;
  header_variables?: string[];
  body_variables?: string[];
  buttons?: Record<string, unknown>[];
}

export interface SendMessageRequest {
  contact_id: number;
  message_type: string;
  template_name?: string;
  template_variables?: Record<string, unknown>;
  content?: string;
  media_url?: string;
  scheduled_at?: string;
}
