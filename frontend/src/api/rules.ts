/**
 * Stratum AI - Automation Rules API
 *
 * Automation rules builder and execution endpoints
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// Types
export type RuleStatus = 'active' | 'paused' | 'draft'
export type RuleTrigger = 'schedule' | 'metric_threshold' | 'event' | 'manual'
export type RuleAction = 'pause_campaign' | 'adjust_budget' | 'adjust_bid' | 'send_alert' | 'pause_asset'
export type ConditionOperator = 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq' | 'between'

export interface RuleCondition {
  metric: string
  operator: ConditionOperator
  value: number | [number, number]
  window?: string // e.g., '24h', '7d'
}

export interface RuleActionConfig {
  type: RuleAction
  params: Record<string, unknown>
}

export interface Rule {
  id: string
  tenantId: number
  name: string
  description: string | null
  status: RuleStatus
  trigger: RuleTrigger
  conditions: RuleCondition[]
  conditionLogic: 'and' | 'or'
  actions: RuleActionConfig[]
  platforms: string[]
  campaignIds: string[] | null // null = all campaigns
  schedule?: {
    cron?: string
    timezone: string
  }
  createdAt: string
  updatedAt: string
  lastRunAt: string | null
  runCount: number
}

export interface RuleExecution {
  id: string
  ruleId: string
  status: 'success' | 'failed' | 'skipped'
  triggeredAt: string
  completedAt: string | null
  affectedCampaigns: string[]
  actionsExecuted: {
    type: RuleAction
    campaignId: string
    result: 'success' | 'failed'
    details: Record<string, unknown>
  }[]
  error: string | null
}

export interface RuleFilters {
  status?: RuleStatus
  trigger?: RuleTrigger
  platform?: string
  search?: string
  skip?: number
  limit?: number
}

export interface CreateRuleRequest {
  name: string
  description?: string
  trigger: RuleTrigger
  conditions: RuleCondition[]
  conditionLogic?: 'and' | 'or'
  actions: RuleActionConfig[]
  platforms?: string[]
  campaignIds?: string[]
  schedule?: {
    cron?: string
    timezone?: string
  }
}

export interface UpdateRuleRequest extends Partial<CreateRuleRequest> {
  status?: RuleStatus
}

// API Functions
export const rulesApi = {
  /**
   * Get all rules with optional filters
   */
  getRules: async (filters: RuleFilters = {}): Promise<PaginatedResponse<Rule>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<Rule>>>(
      '/rules',
      { params: filters }
    )
    return response.data.data
  },

  /**
   * Get a single rule by ID
   */
  getRule: async (id: string): Promise<Rule> => {
    const response = await apiClient.get<ApiResponse<Rule>>(`/rules/${id}`)
    return response.data.data
  },

  /**
   * Create a new rule
   */
  createRule: async (data: CreateRuleRequest): Promise<Rule> => {
    const response = await apiClient.post<ApiResponse<Rule>>('/rules', data)
    return response.data.data
  },

  /**
   * Update an existing rule
   */
  updateRule: async (id: string, data: UpdateRuleRequest): Promise<Rule> => {
    const response = await apiClient.patch<ApiResponse<Rule>>(`/rules/${id}`, data)
    return response.data.data
  },

  /**
   * Delete a rule
   */
  deleteRule: async (id: string): Promise<void> => {
    await apiClient.delete(`/rules/${id}`)
  },

  /**
   * Toggle rule status
   */
  toggleRule: async (id: string): Promise<Rule> => {
    const response = await apiClient.post<ApiResponse<Rule>>(`/rules/${id}/toggle`)
    return response.data.data
  },

  /**
   * Duplicate (copy) a rule
   */
  duplicateRule: async (id: string): Promise<Rule> => {
    const response = await apiClient.post<ApiResponse<Rule>>(`/rules/${id}/duplicate`)
    return response.data.data
  },

  /**
   * Execute a rule manually
   */
  executeRule: async (id: string): Promise<RuleExecution> => {
    const response = await apiClient.post<ApiResponse<RuleExecution>>(`/rules/${id}/execute`)
    return response.data.data
  },

  /**
   * Get rule execution history
   */
  getRuleExecutions: async (
    id: string,
    limit: number = 10
  ): Promise<RuleExecution[]> => {
    const response = await apiClient.get<ApiResponse<RuleExecution[]>>(
      `/rules/${id}/executions`,
      { params: { limit } }
    )
    return response.data.data
  },

  /**
   * Get rule templates
   */
  getTemplates: async (): Promise<Partial<Rule>[]> => {
    const response = await apiClient.get<ApiResponse<Partial<Rule>[]>>('/rules/templates')
    return response.data.data
  },

  /**
   * Validate rule conditions
   */
  validateConditions: async (conditions: RuleCondition[]): Promise<{ valid: boolean; errors: string[] }> => {
    const response = await apiClient.post<ApiResponse<{ valid: boolean; errors: string[] }>>(
      '/rules/validate',
      { conditions }
    )
    return response.data.data
  },
}

// React Query Hooks

export function useRules(filters: RuleFilters = {}) {
  return useQuery({
    queryKey: ['rules', filters],
    queryFn: () => rulesApi.getRules(filters),
    staleTime: 30 * 1000,
  })
}

export function useRule(id: string) {
  return useQuery({
    queryKey: ['rules', id],
    queryFn: () => rulesApi.getRule(id),
    enabled: !!id,
  })
}

export function useCreateRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: rulesApi.createRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
    onError: (error: any) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useUpdateRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateRuleRequest }) =>
      rulesApi.updateRule(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      queryClient.invalidateQueries({ queryKey: ['rules', variables.id] })
    },
    onError: (error: any) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useDeleteRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: rulesApi.deleteRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
    onError: (error: any) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useToggleRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: rulesApi.toggleRule,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      queryClient.invalidateQueries({ queryKey: ['rules', id] })
    },
    onError: (error: any) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useDuplicateRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: rulesApi.duplicateRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
    onError: (error: any) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useExecuteRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: rulesApi.executeRule,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['rules', id, 'executions'] })
    },
  })
}

export function useRuleExecutions(id: string, limit: number = 10) {
  return useQuery({
    queryKey: ['rules', id, 'executions', limit],
    queryFn: () => rulesApi.getRuleExecutions(id, limit),
    enabled: !!id,
  })
}

export function useRuleTemplates() {
  return useQuery({
    queryKey: ['rules', 'templates'],
    queryFn: rulesApi.getTemplates,
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

export function useValidateConditions() {
  return useMutation({
    mutationFn: rulesApi.validateConditions,
  })
}
