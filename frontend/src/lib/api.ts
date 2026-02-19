/**
 * API utility module — DEPRECATED
 *
 * This module now re-exports the canonical API client from `@/api/client`.
 * All new code should import directly from `@/api/client` instead.
 *
 * Kept for backward compatibility with existing imports.
 */

import { apiClient } from '@/api/client';
export type { ApiResponse } from '@/api/client';

/**
 * Thin wrapper that provides the same `.get()` / `.post()` interface as the
 * old fetch-based `ApiClient` class, but delegates to the shared axios instance
 * (which handles auth tokens, tenant headers, and token refresh).
 */
const api = {
  async get<T = any>(endpoint: string, params?: Record<string, string>) {
    let url = endpoint;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url = `${endpoint}?${searchParams.toString()}`;
    }
    const response = await apiClient.get<T>(url);
    return response;
  },

  async post<T = any>(endpoint: string, data?: unknown) {
    const response = await apiClient.post<T>(endpoint, data);
    return response;
  },

  async put<T = any>(endpoint: string, data?: unknown) {
    const response = await apiClient.put<T>(endpoint, data);
    return response;
  },

  async patch<T = any>(endpoint: string, data?: unknown) {
    const response = await apiClient.patch<T>(endpoint, data);
    return response;
  },

  async delete<T = any>(endpoint: string) {
    const response = await apiClient.delete<T>(endpoint);
    return response;
  },
};

export default api;
