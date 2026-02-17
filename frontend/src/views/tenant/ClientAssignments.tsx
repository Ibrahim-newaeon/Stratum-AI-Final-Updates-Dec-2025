/**
 * Client Assignments Management - Gap #4
 *
 * UI for ADMIN+ roles to manage MANAGER/ANALYST → Client assignments.
 * Connects to backend ClientAssignment model via API endpoints.
 *
 * Features:
 * - View all client assignments for the tenant
 * - Assign users (MANAGER/ANALYST) to clients
 * - Remove assignments
 * - Set primary client for a user
 */

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { meetsRoleRequirement } from '@/components/auth/ProtectedRoute';
import {
  UserGroupIcon,
  PlusIcon,
  TrashIcon,
  StarIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';

// Types
interface Client {
  id: number;
  name: string;
  domain: string | null;
  status: 'active' | 'inactive';
  campaign_count: number;
}

interface AssignedUser {
  id: number;
  email: string;
  full_name: string;
  role: 'manager' | 'analyst';
  is_primary: boolean;
  assigned_at: string;
}

interface ClientWithAssignments extends Client {
  assignments: AssignedUser[];
}

interface AvailableUser {
  id: number;
  email: string;
  full_name: string;
  role: 'manager' | 'analyst';
}

// Mock data (would be fetched from API)
const MOCK_CLIENTS: ClientWithAssignments[] = [
  {
    id: 1,
    name: 'Acme Commerce',
    domain: 'acme.com',
    status: 'active',
    campaign_count: 12,
    assignments: [
      {
        id: 1,
        email: 'sarah@stratum.ai',
        full_name: 'Sarah Manager',
        role: 'manager',
        is_primary: true,
        assigned_at: '2025-01-15',
      },
      {
        id: 2,
        email: 'john@stratum.ai',
        full_name: 'John Analyst',
        role: 'analyst',
        is_primary: false,
        assigned_at: '2025-02-01',
      },
    ],
  },
  {
    id: 2,
    name: 'TechStart Inc',
    domain: 'techstart.io',
    status: 'active',
    campaign_count: 5,
    assignments: [
      {
        id: 3,
        email: 'mike@stratum.ai',
        full_name: 'Mike Manager',
        role: 'manager',
        is_primary: true,
        assigned_at: '2025-01-20',
      },
    ],
  },
  {
    id: 3,
    name: 'GreenLeaf Co',
    domain: 'greenleaf.co',
    status: 'active',
    campaign_count: 8,
    assignments: [],
  },
];

const MOCK_AVAILABLE_USERS: AvailableUser[] = [
  { id: 1, email: 'sarah@stratum.ai', full_name: 'Sarah Manager', role: 'manager' },
  { id: 2, email: 'john@stratum.ai', full_name: 'John Analyst', role: 'analyst' },
  { id: 3, email: 'mike@stratum.ai', full_name: 'Mike Manager', role: 'manager' },
  { id: 4, email: 'anna@stratum.ai', full_name: 'Anna Analyst', role: 'analyst' },
  { id: 5, email: 'tom@stratum.ai', full_name: 'Tom Manager', role: 'manager' },
];

export default function ClientAssignments() {
  const { user } = useAuth();
  const [clients, setClients] = useState<ClientWithAssignments[]>(MOCK_CLIENTS);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedClient, setSelectedClient] = useState<ClientWithAssignments | null>(null);
  const [assignSearch, setAssignSearch] = useState('');
  const [confirmRemove, setConfirmRemove] = useState<{ clientId: number; userId: number } | null>(null);

  const isAdmin = user?.role && meetsRoleRequirement(user.role, 'admin');

  const filteredClients = clients.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.domain?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenAssignModal = (client: ClientWithAssignments) => {
    setSelectedClient(client);
    setAssignSearch('');
    setShowAssignModal(true);
  };

  const getAvailableUsersForClient = (client: ClientWithAssignments) => {
    const assignedIds = new Set(client.assignments.map((a) => a.id));
    return MOCK_AVAILABLE_USERS.filter(
      (u) =>
        !assignedIds.has(u.id) &&
        u.full_name.toLowerCase().includes(assignSearch.toLowerCase())
    );
  };

  const handleAssignUser = (clientId: number, userId: number) => {
    const availableUser = MOCK_AVAILABLE_USERS.find((u) => u.id === userId);
    if (!availableUser) return;

    setClients((prev) =>
      prev.map((c) => {
        if (c.id !== clientId) return c;
        return {
          ...c,
          assignments: [
            ...c.assignments,
            {
              id: availableUser.id,
              email: availableUser.email,
              full_name: availableUser.full_name,
              role: availableUser.role,
              is_primary: c.assignments.length === 0, // First assignment is primary
              assigned_at: new Date().toISOString().split('T')[0],
            },
          ],
        };
      })
    );
    // In production: POST /api/v1/clients/{clientId}/assignments { user_id, is_primary }
  };

  const handleRemoveAssignment = (clientId: number, userId: number) => {
    setClients((prev) =>
      prev.map((c) => {
        if (c.id !== clientId) return c;
        return {
          ...c,
          assignments: c.assignments.filter((a) => a.id !== userId),
        };
      })
    );
    setConfirmRemove(null);
    // In production: DELETE /api/v1/clients/{clientId}/assignments/{userId}
  };

  const handleTogglePrimary = (clientId: number, userId: number) => {
    setClients((prev) =>
      prev.map((c) => {
        if (c.id !== clientId) return c;
        return {
          ...c,
          assignments: c.assignments.map((a) => ({
            ...a,
            is_primary: a.id === userId,
          })),
        };
      })
    );
    // In production: PATCH /api/v1/clients/{clientId}/assignments/{userId} { is_primary: true }
  };

  const roleBadge = (role: string) => {
    const config =
      role === 'manager'
        ? { bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/20' }
        : { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' };
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text} border ${config.border} capitalize`}
      >
        {role}
      </span>
    );
  };

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <ExclamationTriangleIcon className="w-12 h-12 text-amber-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-foreground">Access Restricted</h3>
          <p className="text-muted-foreground text-sm mt-1">
            Only Admin and Super Admin users can manage client assignments.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Client Assignments</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Assign managers and analysts to specific clients for scoped access.
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search clients..."
          className="w-full pl-10 pr-4 py-2.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50"
        />
      </div>

      {/* Client Cards */}
      <div className="grid gap-4">
        {filteredClients.map((client) => (
          <div
            key={client.id}
            className="bg-card border border-border rounded-xl overflow-hidden"
          >
            {/* Client Header */}
            <div className="flex items-center justify-between p-5 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <BuildingOfficeIcon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">{client.name}</h3>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {client.domain && <span>{client.domain}</span>}
                    <span>{client.campaign_count} campaigns</span>
                    <span
                      className={`inline-flex items-center gap-1 ${
                        client.status === 'active' ? 'text-emerald-400' : 'text-amber-400'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          client.status === 'active' ? 'bg-emerald-400' : 'bg-amber-400'
                        }`}
                      />
                      {client.status}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleOpenAssignModal(client)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-sm font-medium hover:bg-primary/20 transition-colors"
              >
                <PlusIcon className="w-4 h-4" />
                Assign User
              </button>
            </div>

            {/* Assignments List */}
            {client.assignments.length === 0 ? (
              <div className="p-6 text-center">
                <UserGroupIcon className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No users assigned to this client</p>
                <button
                  onClick={() => handleOpenAssignModal(client)}
                  className="mt-2 text-sm text-primary hover:text-primary/80 transition-colors"
                >
                  Assign someone
                </button>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {client.assignments.map((assignment) => (
                  <div
                    key={assignment.id}
                    className="flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        <UserIcon className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">
                            {assignment.full_name}
                          </span>
                          {roleBadge(assignment.role)}
                          {assignment.is_primary && (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <StarIconSolid className="w-3 h-3" />
                              Primary
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground">{assignment.email}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!assignment.is_primary && (
                        <button
                          onClick={() => handleTogglePrimary(client.id, assignment.id)}
                          className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                          title="Set as primary"
                        >
                          <StarIcon className="w-4 h-4 text-muted-foreground" />
                        </button>
                      )}
                      {confirmRemove?.clientId === client.id &&
                      confirmRemove?.userId === assignment.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleRemoveAssignment(client.id, assignment.id)}
                            className="p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                            title="Confirm remove"
                          >
                            <CheckIcon className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setConfirmRemove(null)}
                            className="p-1.5 rounded-lg hover:bg-accent transition-colors"
                            title="Cancel"
                          >
                            <XMarkIcon className="w-4 h-4 text-muted-foreground" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() =>
                            setConfirmRemove({ clientId: client.id, userId: assignment.id })
                          }
                          className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                          title="Remove assignment"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredClients.length === 0 && (
        <div className="text-center py-12">
          <BuildingOfficeIcon className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-muted-foreground">No clients found matching your search.</p>
        </div>
      )}

      {/* Assign User Modal */}
      {showAssignModal && selectedClient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowAssignModal(false)}
          />
          <div className="relative bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <div>
                <h3 className="text-lg font-semibold text-foreground">Assign User</h3>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Assign a manager or analyst to{' '}
                  <span className="text-foreground font-medium">{selectedClient.name}</span>
                </p>
              </div>
              <button
                onClick={() => setShowAssignModal(false)}
                className="p-1.5 rounded-lg hover:bg-accent transition-colors"
              >
                <XMarkIcon className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            <div className="p-5">
              {/* Search */}
              <div className="relative mb-4">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  value={assignSearch}
                  onChange={(e) => setAssignSearch(e.target.value)}
                  placeholder="Search users..."
                  className="w-full pl-10 pr-4 py-2.5 bg-background border border-border rounded-lg text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>

              {/* Available Users */}
              <div className="max-h-64 overflow-y-auto space-y-1">
                {getAvailableUsersForClient(selectedClient).map((availUser) => (
                  <button
                    key={availUser.id}
                    onClick={() => {
                      handleAssignUser(selectedClient.id, availUser.id);
                      setShowAssignModal(false);
                    }}
                    className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-accent transition-colors text-left"
                  >
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                      <UserIcon className="w-4 h-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {availUser.full_name}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">{availUser.email}</p>
                    </div>
                    {roleBadge(availUser.role)}
                  </button>
                ))}
                {getAvailableUsersForClient(selectedClient).length === 0 && (
                  <p className="text-center text-sm text-muted-foreground py-6">
                    No available users to assign
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
