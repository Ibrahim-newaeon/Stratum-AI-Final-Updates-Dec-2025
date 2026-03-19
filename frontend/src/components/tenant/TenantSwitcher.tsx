/**
 * Tenant Switcher - Multi-Account/Workspace Switcher
 *
 * Dropdown in the dashboard header that allows users with memberships
 * in multiple tenants to switch between them. On switch, new JWT tokens
 * are issued scoped to the selected tenant.
 *
 * Behavior:
 * - Hidden if user belongs to only 1 tenant (or 0)
 * - Shows dropdown with all available tenants and the user's role in each
 * - Highlights the currently active tenant
 * - On switch: calls POST /auth/switch-tenant, stores new tokens,
 *   updates tenant store, and reloads dashboard data
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTenantStore } from '@/stores/tenantStore';
import apiClient, { setAccessToken, setTenantId as setApiTenantId } from '@/api/client';
import {
  BuildingOffice2Icon,
  ChevronUpDownIcon,
  CheckIcon,
  ArrowsRightLeftIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface TenantMembership {
  tenant_id: number;
  tenant_name: string;
  tenant_slug: string;
  tenant_plan: string;
  role: string;
  is_default: boolean;
  is_active: boolean;
}

export default function TenantSwitcher() {
  const { updateUser } = useAuth();
  const { tenantId, setTenantId, setTenant } = useTenantStore();
  const [tenants, setTenants] = useState<TenantMembership[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch available tenants on mount
  useEffect(() => {
    if (loaded) return;

    apiClient
      .get('/auth/tenants')
      .then((res) => {
        const data = res.data?.data || res.data || [];
        if (Array.isArray(data)) {
          setTenants(data);
        }
        setLoaded(true);
      })
      .catch(() => {
        setLoaded(true);
      });
  }, [loaded]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleSwitch = useCallback(
    async (targetTenant: TenantMembership) => {
      if (targetTenant.tenant_id === tenantId || isSwitching) return;

      setIsSwitching(true);
      try {
        const res = await apiClient.post('/auth/switch-tenant', {
          tenant_id: targetTenant.tenant_id,
        });

        const data = res.data?.data || res.data;

        if (data?.access_token) {
          // Store new tokens
          setAccessToken(data.access_token);
          if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
          }

          // Update tenant context
          setApiTenantId(data.tenant_id);
          setTenantId(data.tenant_id);
          setTenant({
            id: data.tenant_id,
            name: data.tenant_name || targetTenant.tenant_name,
            slug: targetTenant.tenant_slug,
            domain: null,
            plan: targetTenant.tenant_plan,
            plan_expires_at: null,
            max_users: 0,
            max_campaigns: 0,
            settings: {},
            feature_flags: {},
            created_at: '',
            updated_at: '',
          });

          // Update auth context user with new role/tenant
          updateUser({
            tenant_id: data.tenant_id,
            role: data.role as any,
          });

          setIsOpen(false);

          // Reload page to reset all data queries for the new tenant
          window.location.reload();
        }
      } catch (err) {
        console.error('[TenantSwitcher] Switch failed:', err);
      } finally {
        setIsSwitching(false);
      }
    },
    [tenantId, isSwitching, setTenantId, setTenant, updateUser]
  );

  // Don't show if user has 0 or 1 tenant
  if (tenants.length <= 1) return null;

  const activeTenant = tenants.find((t) => t.tenant_id === tenantId);
  const activeName = activeTenant?.tenant_name || 'Select Workspace';

  const roleColors: Record<string, string> = {
    superadmin: 'text-purple-400 bg-purple-500/10',
    admin: 'text-blue-400 bg-blue-500/10',
    manager: 'text-teal-400 bg-teal-500/10',
    analyst: 'text-amber-400 bg-amber-500/10',
    viewer: 'text-gray-400 bg-gray-500/10',
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isSwitching}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all text-sm',
          isOpen
            ? 'bg-white/10 border-[#00c7be]/30 text-white'
            : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10 hover:border-white/20'
        )}
      >
        <BuildingOffice2Icon className="w-4 h-4 text-[#00c7be] flex-shrink-0" />
        <span className="truncate max-w-[140px] font-medium">{activeName}</span>
        {isSwitching ? (
          <ArrowsRightLeftIcon className="w-4 h-4 text-[#00c7be] animate-spin flex-shrink-0" />
        ) : (
          <ChevronUpDownIcon className="w-4 h-4 text-white/40 flex-shrink-0" />
        )}
      </button>

      {isOpen && (
        <div
          className="absolute top-full right-0 mt-1.5 w-80 rounded-2xl shadow-2xl z-50 overflow-hidden"
          style={{
            background: 'rgba(11, 18, 21, 0.95)',
            backdropFilter: 'blur(40px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          {/* Header */}
          <div
            className="px-4 py-3"
            style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}
          >
            <p className="text-xs font-medium text-white/50 uppercase tracking-wider">
              Switch Workspace
            </p>
          </div>

          {/* Tenant List */}
          <div className="max-h-72 overflow-y-auto py-1">
            {tenants.map((t) => {
              const isActive = t.tenant_id === tenantId;
              return (
                <button
                  key={t.tenant_id}
                  onClick={() => handleSwitch(t)}
                  disabled={isActive || isSwitching}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                    isActive
                      ? 'bg-[#00c7be]/10'
                      : 'hover:bg-white/5'
                  )}
                >
                  <div
                    className={cn(
                      'w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0',
                      isActive ? 'bg-[#00c7be]/20' : 'bg-white/5'
                    )}
                  >
                    <span
                      className={cn(
                        'text-xs font-bold',
                        isActive ? 'text-[#00c7be]' : 'text-white/50'
                      )}
                    >
                      {t.tenant_name
                        .split(' ')
                        .map((w) => w[0])
                        .join('')
                        .toUpperCase()
                        .slice(0, 2)}
                    </span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        'text-sm font-medium truncate',
                        isActive ? 'text-[#00c7be]' : 'text-white/90'
                      )}
                    >
                      {t.tenant_name}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span
                        className={cn(
                          'text-[10px] font-medium px-1.5 py-0.5 rounded capitalize',
                          roleColors[t.role] || 'text-gray-400 bg-gray-500/10'
                        )}
                      >
                        {t.role}
                      </span>
                      <span className="text-[10px] text-white/30 capitalize">
                        {t.tenant_plan}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {t.is_default && (
                      <span className="text-[10px] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                        Default
                      </span>
                    )}
                    {isActive && <CheckIcon className="w-4 h-4 text-[#00c7be]" />}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Footer */}
          <div
            className="px-4 py-2.5"
            style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}
          >
            <p className="text-[11px] text-white/30">
              {tenants.length} workspace{tenants.length !== 1 ? 's' : ''} available
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
