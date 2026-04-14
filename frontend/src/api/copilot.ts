/**
 * Stratum AI - Copilot Chat API (Feature #4)
 *
 * API client and hooks for the AI Copilot conversational interface.
 */

import { useMutation } from '@tanstack/react-query';
import { apiClient, ApiResponse } from './client';

// =============================================================================
// Types
// =============================================================================

export interface CopilotDataCard {
  label: string;
  value: string;
  change?: number | null;
  status?: string;
}

export interface CopilotMessageRequest {
  message: string;
  session_id?: string;
}

export interface CopilotMessageResponse {
  session_id: string;
  message: string;
  suggestions: string[];
  data_cards: CopilotDataCard[];
  intent: string;
  timestamp: string;
}

export interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  suggestions?: string[];
  data_cards?: CopilotDataCard[];
  intent?: string;
}

// =============================================================================
// API Functions
// =============================================================================

export const copilotApi = {
  sendMessage: async (request: CopilotMessageRequest): Promise<CopilotMessageResponse> => {
    const response = await apiClient.post<ApiResponse<CopilotMessageResponse>>(
      '/copilot/chat',
      request,
    );
    return response.data.data;
  },
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Send a message to the AI Copilot
 */
export function useCopilotChat() {
  return useMutation({
    mutationFn: copilotApi.sendMessage,
  });
}
