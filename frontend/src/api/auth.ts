/**
 * Stratum AI - Auth API
 *
 * Authentication endpoints for signup, login, email verification,
 * password reset, and token management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse, setAccessToken } from './client';

// Types
export interface User {
  id: number;
  email: string;
  name: string;
  role: 'superadmin' | 'admin' | 'user';
  tenant_id: number | null;
  is_active: boolean;
  is_verified: boolean;
  preferences?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
  phone?: string;
  company?: string;
  verification_token?: string;
}

export interface SignupResponse {
  user: User;
  message: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface VerifyEmailResponse {
  success: boolean;
  message: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  success: boolean;
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

export interface ResetPasswordResponse {
  success: boolean;
  message: string;
}

export interface ResendVerificationRequest {
  email: string;
}

export interface ResendVerificationResponse {
  success: boolean;
  message: string;
}

// WhatsApp OTP Types
export interface SendWhatsAppOTPRequest {
  phone_number: string;
}

export interface SendWhatsAppOTPResponse {
  message: string;
  expires_in: number;
}

export interface VerifyWhatsAppOTPRequest {
  phone_number: string;
  otp_code: string;
}

export interface VerifyWhatsAppOTPResponse {
  verified: boolean;
  verification_token: string | null;
}

// API Functions
export const authApi = {
  /**
   * Register a new user
   */
  signup: async (data: SignupRequest): Promise<SignupResponse> => {
    const response = await apiClient.post<ApiResponse<SignupResponse>>('/auth/register', data);
    return response.data.data;
  },

  /**
   * Login with email and password
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<ApiResponse<LoginResponse>>('/auth/login', data);
    return response.data.data;
  },

  /**
   * Verify email with token
   */
  verifyEmail: async (data: VerifyEmailRequest): Promise<VerifyEmailResponse> => {
    const response = await apiClient.post<ApiResponse<VerifyEmailResponse>>(
      '/auth/verify-email',
      data
    );
    return response.data.data;
  },

  /**
   * Request password reset
   */
  forgotPassword: async (data: ForgotPasswordRequest): Promise<ForgotPasswordResponse> => {
    const response = await apiClient.post<ApiResponse<ForgotPasswordResponse>>(
      '/auth/forgot-password',
      data
    );
    return response.data.data;
  },

  /**
   * Reset password with token
   */
  resetPassword: async (data: ResetPasswordRequest): Promise<ResetPasswordResponse> => {
    const response = await apiClient.post<ApiResponse<ResetPasswordResponse>>(
      '/auth/reset-password',
      data
    );
    return response.data.data;
  },

  /**
   * Resend verification email
   */
  resendVerification: async (
    data: ResendVerificationRequest
  ): Promise<ResendVerificationResponse> => {
    const response = await apiClient.post<ApiResponse<ResendVerificationResponse>>(
      '/auth/resend-verification',
      data
    );
    return response.data.data;
  },

  /**
   * Send WhatsApp OTP for phone verification
   */
  sendWhatsAppOTP: async (data: SendWhatsAppOTPRequest): Promise<SendWhatsAppOTPResponse> => {
    const response = await apiClient.post<ApiResponse<SendWhatsAppOTPResponse>>(
      '/auth/whatsapp/send-otp',
      data
    );
    return response.data.data;
  },

  /**
   * Verify WhatsApp OTP code
   */
  verifyWhatsAppOTP: async (data: VerifyWhatsAppOTPRequest): Promise<VerifyWhatsAppOTPResponse> => {
    const response = await apiClient.post<ApiResponse<VerifyWhatsAppOTPResponse>>(
      '/auth/whatsapp/verify-otp',
      data
    );
    return response.data.data;
  },

  /**
   * Logout - invalidate tokens
   */
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  /**
   * Get current user profile
   */
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<ApiResponse<User>>('/auth/me');
    return response.data.data;
  },

  /**
   * Update current user preferences
   */
  updatePreferences: async (preferences: Record<string, unknown>): Promise<User> => {
    const response = await apiClient.patch<ApiResponse<User>>('/users/me', { preferences });
    return response.data.data;
  },

  /**
   * Refresh access token
   */
  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await apiClient.post<ApiResponse<AuthTokens>>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data.data;
  },
};

// React Query Hooks

/**
 * Hook for user signup
 */
export function useSignup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.signup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
}

/**
 * Hook for user login
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      setAccessToken(data.tokens.access_token);
      localStorage.setItem('refresh_token', data.tokens.refresh_token);
      queryClient.setQueryData(['auth', 'user'], data.user);
    },
  });
}

/**
 * Hook for email verification
 */
export function useVerifyEmail() {
  return useMutation({
    mutationFn: authApi.verifyEmail,
  });
}

/**
 * Hook for forgot password
 */
export function useForgotPassword() {
  return useMutation({
    mutationFn: authApi.forgotPassword,
  });
}

/**
 * Hook for password reset
 */
export function useResetPassword() {
  return useMutation({
    mutationFn: authApi.resetPassword,
  });
}

/**
 * Hook for resending verification email
 */
export function useResendVerification() {
  return useMutation({
    mutationFn: authApi.resendVerification,
  });
}

/**
 * Hook for logout
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      setAccessToken(null);
      localStorage.removeItem('refresh_token');
      queryClient.clear();
    },
  });
}

/**
 * Hook for getting current user
 */
export function useCurrentUser(enabled = true) {
  return useQuery({
    queryKey: ['auth', 'user'],
    queryFn: authApi.getCurrentUser,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}

/**
 * Hook for updating user notification preferences
 */
export function useUpdatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.updatePreferences,
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(['auth', 'user'], updatedUser);
    },
  });
}

/**
 * Hook for sending WhatsApp OTP
 */
export function useSendWhatsAppOTP() {
  return useMutation({
    mutationFn: authApi.sendWhatsAppOTP,
  });
}

/**
 * Hook for verifying WhatsApp OTP
 */
export function useVerifyWhatsAppOTP() {
  return useMutation({
    mutationFn: authApi.verifyWhatsAppOTP,
  });
}
