/**
 * Client Context Switcher - Gap #5
 *
 * Dropdown component for MANAGER/ANALYST roles to switch between
 * their assigned clients. Placed in the dashboard header.
 *
 * Behavior:
 * - SUPERADMIN/ADMIN: Hidden (they have unrestricted access)
 * - MANAGER/ANALYST: Shows dropdown of assigned clients
 * - VIEWER: Hidden (only has access to one client via User.client_id)
 *
 * Uses Zustand store for persisted active client state.
 */

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  BuildingOfficeIcon,
  ChevronUpDownIcon,
  CheckIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// ── Client Context Store ────────────────────────────────────────────────────
interface AssignedClient {
  id: number;
  name: string;
  domain: string | null;
  is_primary: boolean;
}

interface ClientContextState {
  activeClientId: number | null;
  activeClientName: string | null;
  assignedClients: AssignedClient[];
  setActiveClient: (id: number, name: string) => void;
  setAssignedClients: (clients: AssignedClient[]) => void;
  clearClientContext: () => void;
}

export const useClientContext = create<ClientContextState>()(
  persist(
    (set) => ({
      activeClientId: null,
      activeClientName: null,
      assignedClients: [],

      setActiveClient: (id, name) =>
        set({ activeClientId: id, activeClientName: name }),

      setAssignedClients: (clients) => {
        set({ assignedClients: clients });
        // Auto-select primary client if no active selection
        const primary = clients.find((c) => c.is_primary);
        if (primary) {
          set({ activeClientId: primary.id, activeClientName: primary.name });
        } else if (clients.length > 0) {
          set({ activeClientId: clients[0].id, activeClientName: clients[0].name });
        }
      },

      clearClientContext: () =>
        set({
          activeClientId: null,
          activeClientName: null,
          assignedClients: [],
        }),
    }),
    {
      name: 'stratum-client-context',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        activeClientId: state.activeClientId,
        activeClientName: state.activeClientName,
      }),
    }
  )
);

import apiClient from '@/api/client';

// ── Component ───────────────────────────────────────────────────────────────
interface ClientContextSwitcherProps {
  className?: string;
}

export default function ClientContextSwitcher({ className }: ClientContextSwitcherProps) {
  const { user } = useAuth();
  const {
    activeClientId,
    activeClientName,
    assignedClients,
    setActiveClient,
    setAssignedClients,
  } = useClientContext();

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Only show for MANAGER and ANALYST roles
  const shouldShow =
    user?.role === 'manager' || user?.role === 'analyst';

  // Load assigned clients on mount from API
  useEffect(() => {
    if (shouldShow && assignedClients.length === 0) {
      apiClient.get('/users/me/assigned-clients')
        .then((res) => {
          const clients = res.data?.data || res.data || [];
          if (Array.isArray(clients) && clients.length > 0) {
            setAssignedClients(clients);
          }
        })
        .catch(() => {
          // Silently handle — empty client list will show "Select Client"
        });
    }
  }, [shouldShow, assignedClients.length, setAssignedClients]);

  // Close dropdown on click outside
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

  if (!shouldShow) return null;

  const filteredClients = assignedClients.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.domain?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all text-sm',
          isOpen
            ? 'bg-accent border-primary/30 text-foreground'
            : 'bg-card border-border text-foreground hover:bg-accent hover:border-border'
        )}
      >
        <BuildingOfficeIcon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        <span className="truncate max-w-[150px] font-medium">
          {activeClientName || 'Select Client'}
        </span>
        <ChevronUpDownIcon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden">
          {/* Search */}
          {assignedClients.length > 3 && (
            <div className="p-2 border-b border-border">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search clients..."
                  autoFocus
                  className="w-full pl-8 pr-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
            </div>
          )}

          {/* Client List */}
          <div className="max-h-64 overflow-y-auto py-1">
            {filteredClients.map((client) => {
              const isActive = client.id === activeClientId;
              return (
                <button
                  key={client.id}
                  onClick={() => {
                    setActiveClient(client.id, client.name);
                    setIsOpen(false);
                    setSearchQuery('');
                  }}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors',
                    isActive ? 'bg-primary/10' : 'hover:bg-accent'
                  )}
                >
                  <div
                    className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                      isActive ? 'bg-primary/20' : 'bg-muted'
                    )}
                  >
                    <BuildingOfficeIcon
                      className={cn('w-4 h-4', isActive ? 'text-primary' : 'text-muted-foreground')}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        'text-sm font-medium truncate',
                        isActive ? 'text-primary' : 'text-foreground'
                      )}
                    >
                      {client.name}
                    </p>
                    {client.domain && (
                      <p className="text-xs text-muted-foreground truncate">{client.domain}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {client.is_primary && (
                      <span className="text-[10px] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                        Primary
                      </span>
                    )}
                    {isActive && <CheckIcon className="w-4 h-4 text-primary" />}
                  </div>
                </button>
              );
            })}
            {filteredClients.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-4">No clients found</p>
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-2 border-t border-border">
            <p className="text-[11px] text-muted-foreground">
              {assignedClients.length} client{assignedClients.length !== 1 ? 's' : ''} assigned to
              you
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
