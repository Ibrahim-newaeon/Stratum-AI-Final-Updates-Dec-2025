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

export interface CopilotCitation {
  source_path: string;
  title: string;
  distance: number;
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
  citations?: CopilotCitation[];
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
  citations?: CopilotCitation[];
}

// =============================================================================
// API Functions
// =============================================================================

export const copilotApi = {
  sendMessage: async (request: CopilotMessageRequest): Promise<CopilotMessageResponse> => {
    const response = await apiClient.post<ApiResponse<CopilotMessageResponse>>(
      '/copilot/chat',
      request
    );
    return response.data.data;
  },
};

// =============================================================================
// Streaming
// =============================================================================

/**
 * Callback shape for the streaming consumer below.
 *
 * The bridge emits `session` once, then zero-or-more `token` events,
 * optionally one `error` event (timeout / SDK failure), then exactly
 * one `meta` event before `[DONE]`. If `meta.fallback_message` is
 * present, the dashboard should *replace* the streamed bubble with
 * `fallback_message` — the LLM produced nothing usable.
 */
export interface CopilotStreamHandlers {
  onSession?: (sessionId: string) => void;
  onToken: (text: string) => void;
  onMeta: (meta: {
    intent: string;
    suggestions: string[];
    data_cards: CopilotDataCard[];
    citations: CopilotCitation[];
    fallback_message?: string | null;
  }) => void;
  onError?: (reason: string) => void;
  onDone?: () => void;
}

/**
 * POST /copilot/chat/stream and parse the SSE stream.
 *
 * Throws on network failure before the first byte; otherwise drains
 * the stream and resolves when [DONE] is seen. EventSource isn't
 * usable here because the spec is GET-only and we need POST + auth
 * headers, so we hand-roll a minimal parser over fetch's
 * ReadableStream.
 */
export async function streamCopilotMessage(
  request: CopilotMessageRequest,
  handlers: CopilotStreamHandlers,
  options: { signal?: AbortSignal } = {}
): Promise<void> {
  const baseURL =
    apiClient.defaults?.baseURL ??
    (import.meta.env.VITE_API_URL as string | undefined) ??
    '';
  const token = sessionStorage.getItem('access_token') ?? '';

  const response = await fetch(`${baseURL}/copilot/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(request),
    signal: options.signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Copilot stream failed: HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const dispatch = (rawEvent: string) => {
    if (!rawEvent.trim()) return;
    let eventName = 'message';
    const dataLines: string[] = [];
    for (const line of rawEvent.split('\n')) {
      if (line.startsWith('event: ')) {
        eventName = line.slice('event: '.length).trim();
      } else if (line.startsWith('data: ')) {
        dataLines.push(line.slice('data: '.length));
      }
    }
    const data = dataLines.join('\n');

    if (data === '[DONE]') {
      handlers.onDone?.();
      return;
    }
    switch (eventName) {
      case 'session':
        handlers.onSession?.(data);
        break;
      case 'token':
        handlers.onToken(data);
        break;
      case 'meta':
        try {
          const parsed = JSON.parse(data);
          handlers.onMeta({
            intent: parsed.intent ?? 'unknown',
            suggestions: parsed.suggestions ?? [],
            data_cards: parsed.data_cards ?? [],
            citations: parsed.citations ?? [],
            fallback_message: parsed.fallback_message ?? null,
          });
        } catch {
          handlers.onError?.('meta_parse_error');
        }
        break;
      case 'error':
        handlers.onError?.(data);
        break;
      // 'message' (no event:) is unused by our backend; ignore.
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Events are delimited by a blank line — i.e. \n\n.
    let separator: number;
    while ((separator = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);
      dispatch(rawEvent);
    }
  }
  // Flush any trailing event the server didn't terminate (defensive).
  if (buffer.trim()) {
    dispatch(buffer);
  }
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Send a message to the AI Copilot (non-streaming)
 */
export function useCopilotChat() {
  return useMutation({
    mutationFn: copilotApi.sendMessage,
  });
}
