/**
 * Stratum AI - Admin API
 *
 * User and tenant management endpoints (Super Admin)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse, PaginatedResponse } from './client';

// Types
export type UserRole = 'superadmin' | 'admin' | 'user' | 'viewer';
export type TenantStatus = 'active' | 'suspended' | 'trial' | 'churned';
export type PlanTier = 'starter' | 'pro' | 'enterprise';

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  tenantId: number | null;
  isActive: boolean;
  isVerified: boolean;
  lastLoginAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Tenant {
  id: number;
  name: string;
  domain: string | null;
  status: TenantStatus;
  plan: PlanTier;
  settings: Record<string, unknown>;
  userCount: number;
  monthlySpend: number;
  createdAt: string;
  updatedAt: string;
}

export interface TenantWithMetrics extends Tenant {
  emqScore: number | null;
  budgetAtRisk: number;
  activeIncidents: number;
  lastActivityAt: string | null;
}

export interface UserFilters {
  role?: UserRole;
  tenantId?: number;
  isActive?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface TenantFilters {
  status?: TenantStatus;
  plan?: PlanTier;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
  role: UserRole;
  tenantId?: number;
}

export interface UpdateUserRequest {
  name?: string;
  role?: UserRole;
  tenantId?: number;
  isActive?: boolean;
}

export interface CreateTenantRequest {
  name: string;
  domain?: string;
  plan: PlanTier;
  settings?: Record<string, unknown>;
}

export interface UpdateTenantRequest {
  name?: string;
  domain?: string;
  status?: TenantStatus;
  plan?: PlanTier;
  settings?: Record<string, unknown>;
}

// API Functions
export const adminApi = {
  // User Management
  getUsers: async (filters: UserFilters = {}): Promise<PaginatedResponse<User>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<User>>>('/admin/users', {
      params: filters,
    });
    return response.data.data;
  },

  getUser: async (id: number): Promise<User> => {
    const response = await apiClient.get<ApiResponse<User>>(`/admin/users/${id}`);
    return response.data.data;
  },

  createUser: async (data: CreateUserRequest): Promise<User> => {
    const response = await apiClient.post<ApiResponse<User>>('/admin/users', data);
    return response.data.data;
  },

  updateUser: async (id: number, data: UpdateUserRequest): Promise<User> => {
    const response = await apiClient.patch<ApiResponse<User>>(`/admin/users/${id}`, data);
    return response.data.data;
  },

  deleteUser: async (id: number): Promise<void> => {
    await apiClient.delete(`/admin/users/${id}`);
  },

  resetUserPassword: async (id: number): Promise<{ temporaryPassword: string }> => {
    const response = await apiClient.post<ApiResponse<{ temporaryPassword: string }>>(
      `/admin/users/${id}/reset-password`
    );
    return response.data.data;
  },

  // Tenant Management
  getTenants: async (
    filters: TenantFilters = {}
  ): Promise<PaginatedResponse<TenantWithMetrics>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<TenantWithMetrics>>>(
      '/admin/tenants',
      { params: filters }
    );
    return response.data.data;
  },

  getTenant: async (id: number): Promise<TenantWithMetrics> => {
    const response = await apiClient.get<ApiResponse<TenantWithMetrics>>(`/admin/tenants/${id}`);
    return response.data.data;
  },

  createTenant: async (data: CreateTenantRequest): Promise<Tenant> => {
    const response = await apiClient.post<ApiResponse<Tenant>>('/admin/tenants', data);
    return response.data.data;
  },

  updateTenant: async (id: number, data: UpdateTenantRequest): Promise<Tenant> => {
    const response = await apiClient.patch<ApiResponse<Tenant>>(`/admin/tenants/${id}`, data);
    return response.data.data;
  },

  deleteTenant: async (id: number): Promise<void> => {
    await apiClient.delete(`/admin/tenants/${id}`);
  },

  suspendTenant: async (id: number, reason?: string): Promise<Tenant> => {
    const response = await apiClient.post<ApiResponse<Tenant>>(`/admin/tenants/${id}/suspend`, {
      reason,
    });
    return response.data.data;
  },

  reactivateTenant: async (id: number): Promise<Tenant> => {
    const response = await apiClient.post<ApiResponse<Tenant>>(`/admin/tenants/${id}/reactivate`);
    return response.data.data;
  },

  getTenantUsers: async (id: number): Promise<User[]> => {
    const response = await apiClient.get<ApiResponse<User[]>>(`/admin/tenants/${id}/users`);
    return response.data.data;
  },
};

// React Query Hooks

// User hooks
export function useUsers(filters: UserFilters = {}) {
  return useQuery({
    queryKey: ['admin', 'users', filters],
    queryFn: () => adminApi.getUsers(filters),
    staleTime: 30 * 1000,
  });
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ['admin', 'users', id],
    queryFn: () => adminApi.getUser(id),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: adminApi.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateUserRequest }) =>
      adminApi.updateUser(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'users', variables.id] });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: adminApi.deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
  });
}

export function useResetUserPassword() {
  return useMutation({
    mutationFn: adminApi.resetUserPassword,
  });
}

// Tenant hooks
export function useTenants(filters: TenantFilters = {}) {
  return useQuery({
    queryKey: ['admin', 'tenants', filters],
    queryFn: () => adminApi.getTenants(filters),
    staleTime: 30 * 1000,
  });
}

export function useTenant(id: number) {
  return useQuery({
    queryKey: ['admin', 'tenants', id],
    queryFn: () => adminApi.getTenant(id),
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: adminApi.createTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] });
    },
  });
}

export function useUpdateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateTenantRequest }) =>
      adminApi.updateTenant(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', variables.id] });
    },
  });
}

export function useDeleteTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: adminApi.deleteTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] });
    },
  });
}

export function useSuspendTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      adminApi.suspendTenant(id, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', variables.id] });
    },
  });
}

export function useReactivateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: adminApi.reactivateTenant,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', id] });
    },
  });
}

export function useTenantUsers(id: number) {
  return useQuery({
    queryKey: ['admin', 'tenants', id, 'users'],
    queryFn: () => adminApi.getTenantUsers(id),
    enabled: !!id,
  });
}
