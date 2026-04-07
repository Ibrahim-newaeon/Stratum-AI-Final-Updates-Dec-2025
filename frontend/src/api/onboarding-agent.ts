/**
 * Onboarding Agent API Hooks
 *
 * React Query hooks for the conversational onboarding agent.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import api from './client';

// Types
interface StartConversationRequest {
  name?: string;
  email?: string;
  company?: string;
  language?: string;
  is_new_tenant?: boolean;
}

interface StartConversationResponse {
  session_id: string;
  message: string;
  quick_replies: string[];
  state: string;
  progress_percent: number;
}

interface SendMessageRequest {
  session_id: string;
  message: string;
}

interface SendMessageResponse {
  message: string;
  state: string;
  quick_replies: string[];
  progress_percent: number;
  next_step?: string;
  requires_action: boolean;
  action_type?: string;
  action_data: Record<string, unknown>;
  data_collected: Record<string, unknown>;
}

interface ConversationStatusResponse {
  session_id: string;
  state: string;
  progress_percent: number;
  started_at: string;
  last_activity: string;
  onboarding_data: Record<string, unknown>;
}

interface QuickRepliesResponse {
  state: string;
  quick_replies: string[];
}

// API Functions
const onboardingAgentApi = {
  startConversation: async (data: StartConversationRequest): Promise<StartConversationResponse> => {
    const response = await api.post('/onboarding-agent/start', data);
    return response.data;
  },

  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    const response = await api.post('/onboarding-agent/message', data);
    return response.data;
  },

  getStatus: async (sessionId: string): Promise<ConversationStatusResponse> => {
    const response = await api.get(`/onboarding-agent/status/${sessionId}`);
    return response.data;
  },

  completeOnboarding: async (
    sessionId: string
  ): Promise<{ success: boolean; message: string; redirect_to: string }> => {
    const response = await api.post(`/onboarding-agent/complete/${sessionId}`);
    return response.data;
  },

  cancelConversation: async (sessionId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/onboarding-agent/session/${sessionId}`);
    return response.data;
  },

  getQuickReplies: async (state: string): Promise<QuickRepliesResponse> => {
    const response = await api.get(`/onboarding-agent/quick-replies/${state}`);
    return response.data;
  },
};

// Hooks

/**
 * Start a new onboarding conversation
 */
export function useStartConversation() {
  return useMutation({
    mutationFn: onboardingAgentApi.startConversation,
  });
}

/**
 * Send a message to the onboarding agent
 */
export function useSendMessage() {
  return useMutation({
    mutationFn: onboardingAgentApi.sendMessage,
  });
}

/**
 * Get conversation status
 */
export function useConversationStatus(sessionId: string | null) {
  return useQuery({
    queryKey: ['onboarding-agent', 'status', sessionId],
    queryFn: () => onboardingAgentApi.getStatus(sessionId!),
    enabled: !!sessionId,
    refetchInterval: 5000, // Poll every 5 seconds
  });
}

/**
 * Complete the onboarding conversation
 */
export function useCompleteOnboarding() {
  return useMutation({
    mutationFn: onboardingAgentApi.completeOnboarding,
  });
}

/**
 * Cancel/delete a conversation
 */
export function useCancelConversation() {
  return useMutation({
    mutationFn: onboardingAgentApi.cancelConversation,
  });
}

/**
 * Get quick replies for a state
 */
export function useQuickReplies(state: string) {
  return useQuery({
    queryKey: ['onboarding-agent', 'quick-replies', state],
    queryFn: () => onboardingAgentApi.getQuickReplies(state),
    enabled: !!state,
  });
}

export default onboardingAgentApi;
