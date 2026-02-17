/**
 * Stratum AI - Tenant Store
 *
 * Zustand store for managing tenant context and user session state.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { devtools } from 'zustand/middleware'

// =============================================================================
// Types
// =============================================================================

export type UserRole =
  | 'superadmin'
  | 'admin'
  | 'manager'
  | 'media_buyer'
  | 'analyst'
  | 'account_manager'
  | 'viewer'

export interface User {
  id: number
  email: string
  full_name: string | null
  role: UserRole
  avatar_url: string | null
  locale: string
  timezone: string
  is_active: boolean
  is_verified: boolean
  last_login_at: string | null
  created_at: string
}

export interface Tenant {
  id: number
  name: string
  slug: string
  domain: string | null
  plan: string
  plan_expires_at: string | null
  max_users: number
  max_campaigns: number
  settings: Record<string, any>
  feature_flags: Record<string, boolean>
  created_at: string
  updated_at: string
}

export interface TenantState {
  // Current tenant context
  tenantId: number | null
  tenant: Tenant | null

  // Current user
  user: User | null

  // UI state
  isSuperAdminMode: boolean
  superAdminBypass: boolean

  // Date range for analytics
  dateRange: {
    start: string
    end: string
  }

  // Platform filter
  selectedPlatforms: string[]

  // Actions
  setTenantId: (tenantId: number | null) => void
  setTenant: (tenant: Tenant | null) => void
  setUser: (user: User | null) => void
  setSuperAdminMode: (enabled: boolean) => void
  setSuperAdminBypass: (enabled: boolean) => void
  setDateRange: (start: string, end: string) => void
  setSelectedPlatforms: (platforms: string[]) => void
  logout: () => void

  // Computed
  isSuperAdmin: () => boolean
  isAdmin: () => boolean
  hasRole: (roles: UserRole[]) => boolean
  hasFeature: (feature: string) => boolean
}

// =============================================================================
// Store
// =============================================================================

const initialDateRange = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)

  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  }
}

export const useTenantStore = create<TenantState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        tenantId: null,
        tenant: null,
        user: null,
        isSuperAdminMode: false,
        superAdminBypass: false,
        dateRange: initialDateRange(),
        selectedPlatforms: [],

        // Actions
        setTenantId: (tenantId) => {
          set({ tenantId })
          // Also update localStorage for API client
          if (tenantId) {
            localStorage.setItem('tenant_id', String(tenantId))
          } else {
            localStorage.removeItem('tenant_id')
          }
        },

        setTenant: (tenant) => {
          set({ tenant, tenantId: tenant?.id ?? null })
          if (tenant) {
            localStorage.setItem('tenant_id', String(tenant.id))
          }
        },

        setUser: (user) => {
          set({ user })
          // Auto-enable super admin mode if user is superadmin
          if (user?.role === 'superadmin') {
            set({ isSuperAdminMode: true })
          }
        },

        setSuperAdminMode: (enabled) => {
          const state = get()
          // Only allow if user is actually a superadmin
          if (state.user?.role === 'superadmin') {
            set({ isSuperAdminMode: enabled })
          }
        },

        setSuperAdminBypass: (enabled) => {
          const state = get()
          // Only allow if user is superadmin
          if (state.user?.role === 'superadmin') {
            set({ superAdminBypass: enabled })
          }
        },

        setDateRange: (start, end) => {
          set({ dateRange: { start, end } })
        },

        setSelectedPlatforms: (platforms) => {
          set({ selectedPlatforms: platforms })
        },

        logout: () => {
          set({
            tenantId: null,
            tenant: null,
            user: null,
            isSuperAdminMode: false,
            superAdminBypass: false,
            selectedPlatforms: [],
          })
          localStorage.removeItem('tenant_id')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        },

        // Computed
        isSuperAdmin: () => {
          const state = get()
          return state.user?.role === 'superadmin'
        },

        isAdmin: () => {
          const state = get()
          return state.user?.role === 'superadmin' || state.user?.role === 'admin'
        },

        hasRole: (roles) => {
          const state = get()
          if (!state.user) return false
          return roles.includes(state.user.role)
        },

        hasFeature: (feature) => {
          const state = get()
          if (!state.tenant?.feature_flags) return false
          return state.tenant.feature_flags[feature] === true
        },
      }),
      {
        name: 'stratum-tenant-store',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          tenantId: state.tenantId,
          dateRange: state.dateRange,
          selectedPlatforms: state.selectedPlatforms,
          isSuperAdminMode: state.isSuperAdminMode,
        }),
      }
    ),
    { name: 'TenantStore' }
  )
)

// =============================================================================
// Selectors (for optimized re-renders)
// =============================================================================

export const selectTenantId = (state: TenantState) => state.tenantId
export const selectTenant = (state: TenantState) => state.tenant
export const selectUser = (state: TenantState) => state.user
export const selectIsSuperAdminMode = (state: TenantState) => state.isSuperAdminMode
export const selectDateRange = (state: TenantState) => state.dateRange
export const selectSelectedPlatforms = (state: TenantState) => state.selectedPlatforms

// =============================================================================
// Hooks for specific state slices
// =============================================================================

export const useTenantId = () => useTenantStore(selectTenantId)
export const useTenant = () => useTenantStore(selectTenant)
export const useUser = () => useTenantStore(selectUser)
export const useIsSuperAdminMode = () => useTenantStore(selectIsSuperAdminMode)
export const useDateRange = () => useTenantStore(selectDateRange)
export const useSelectedPlatforms = () => useTenantStore(selectSelectedPlatforms)

// =============================================================================
// Action hooks
// =============================================================================

export const useTenantActions = () => {
  const setTenantId = useTenantStore((state) => state.setTenantId)
  const setTenant = useTenantStore((state) => state.setTenant)
  const setUser = useTenantStore((state) => state.setUser)
  const setSuperAdminMode = useTenantStore((state) => state.setSuperAdminMode)
  const setSuperAdminBypass = useTenantStore((state) => state.setSuperAdminBypass)
  const setDateRange = useTenantStore((state) => state.setDateRange)
  const setSelectedPlatforms = useTenantStore((state) => state.setSelectedPlatforms)
  const logout = useTenantStore((state) => state.logout)

  return {
    setTenantId,
    setTenant,
    setUser,
    setSuperAdminMode,
    setSuperAdminBypass,
    setDateRange,
    setSelectedPlatforms,
    logout,
  }
}
