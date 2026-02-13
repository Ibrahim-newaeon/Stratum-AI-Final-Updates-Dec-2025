/**
 * API utility module for making HTTP requests
 */

const API_BASE_URL = (window as any).__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api';

interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

interface ApiError {
  message: string;
  status: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const error: ApiError = {
          message: `HTTP error! status: ${response.status}`,
          status: response.status,
        };
        throw error;
      }

      const data = await response.json();
      return { data, success: true };
    } catch (error) {
      console.error('API request failed:', error);
      return {
        data: null as T,
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    let url = endpoint;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url = `${endpoint}?${searchParams.toString()}`;
    }
    return this.request<T>(url, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // Asset-specific endpoints
  async getAssets() {
    return this.get('/assets');
  }

  async uploadAsset(file: File, metadata?: Record<string, unknown>) {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const url = `${this.baseUrl}/assets/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    return response.json();
  }

  async deleteAsset(assetId: number | string) {
    return this.delete(`/assets/${assetId}`);
  }

  // Campaign endpoints
  async getCampaigns() {
    return this.get('/campaigns');
  }

  async getCampaignById(id: number | string) {
    return this.get(`/campaigns/${id}`);
  }

  // Analytics endpoints
  async getAnalytics(params?: { startDate?: string; endDate?: string; platform?: string }) {
    return this.get('/analytics', params as Record<string, string>);
  }

  // EMQ endpoints
  async getEMQData() {
    return this.get('/emq');
  }

  async getEMQIssues() {
    return this.get('/emq/issues');
  }
}

// Export singleton instance
const api = new ApiClient();
export default api;

// Export class for custom instances
export { ApiClient };
export type { ApiResponse, ApiError };
