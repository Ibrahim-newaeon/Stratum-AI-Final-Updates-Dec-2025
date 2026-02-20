/**
 * CMS User Management
 * List, invite, and manage CMS users with role assignment
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { CMSRole } from '@/api/cms';
import { useCMSPermissions } from '@/hooks/useCMSPermissions';
import {
  MagnifyingGlassIcon,
  PlusIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

// ─── Types ──────────────────────────────────────────────────────────────────

interface CMSUser {
  id: string;
  email: string;
  full_name: string;
  cms_role: CMSRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface InvitePayload {
  email: string;
  full_name: string;
  password: string;
  cms_role: CMSRole;
}

// ─── CMS Role config ───────────────────────────────────────────────────────

const CMS_ROLES: { value: CMSRole; label: string; color: string }[] = [
  { value: 'super_admin', label: 'Super Admin', color: 'text-red-400 bg-red-400/10' },
  { value: 'admin', label: 'Admin', color: 'text-orange-400 bg-orange-400/10' },
  { value: 'editor_in_chief', label: 'Editor-in-Chief', color: 'text-yellow-400 bg-yellow-400/10' },
  { value: 'editor', label: 'Editor', color: 'text-cyan-400 bg-cyan-400/10' },
  { value: 'author', label: 'Author', color: 'text-purple-400 bg-purple-400/10' },
  { value: 'contributor', label: 'Contributor', color: 'text-blue-400 bg-blue-400/10' },
  { value: 'reviewer', label: 'Reviewer', color: 'text-green-400 bg-green-400/10' },
  { value: 'viewer', label: 'Viewer', color: 'text-white/50 bg-white/5' },
];

function getRoleBadge(role: CMSRole) {
  const cfg = CMS_ROLES.find((r) => r.value === role);
  if (!cfg) return { label: role, color: 'text-white/50 bg-white/5' };
  return cfg;
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function CMSUsers() {
  const queryClient = useQueryClient();
  const { hasPermission } = useCMSPermissions();
  const [search, setSearch] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [revokeConfirm, setRevokeConfirm] = useState<string | null>(null);

  // Invite form state
  const [inviteForm, setInviteForm] = useState<InvitePayload>({
    email: '',
    full_name: '',
    password: '',
    cms_role: 'author',
  });
  const [inviteError, setInviteError] = useState<string | null>(null);

  // ─── Queries ────────────────────────────────────────────────────────────

  const {
    data: usersData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['cms-users', search],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      const res = await apiClient.get('/cms/admin/users', { params });
      return res.data?.data?.users as CMSUser[] | undefined;
    },
    staleTime: 30_000,
  });

  const users = usersData || [];

  // ─── Mutations ──────────────────────────────────────────────────────────

  const inviteMutation = useMutation({
    mutationFn: async (payload: InvitePayload) => {
      const res = await apiClient.post('/cms/admin/users/invite', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-users'] });
      setShowInviteModal(false);
      setInviteForm({ email: '', full_name: '', password: '', cms_role: 'author' });
      setInviteError(null);
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Failed to invite user';
      setInviteError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: CMSRole }) => {
      const res = await apiClient.patch(`/cms/admin/users/${userId}/role`, {
        cms_role: role,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-users'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (userId: string) => {
      const res = await apiClient.delete(`/cms/admin/users/${userId}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cms-users'] });
      setRevokeConfirm(null);
    },
  });

  // ─── Handlers ───────────────────────────────────────────────────────────

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError(null);
    if (!inviteForm.email || !inviteForm.full_name || !inviteForm.password) {
      setInviteError('All fields are required.');
      return;
    }
    inviteMutation.mutate(inviteForm);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // ─── Render ─────────────────────────────────────────────────────────────

  if (!hasPermission('manage_users')) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <UserCircleIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-white/60">You do not have permission to manage CMS users.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">CMS Users</h1>
          <p className="text-white/60 mt-1">
            {users.length} user{users.length !== 1 ? 's' : ''} with CMS access
          </p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Invite User
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or email..."
          className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-purple-500/50"
        />
      </div>

      {/* Users Table */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
          </div>
        ) : isError ? (
          <div className="text-center py-20">
            <p className="text-red-400">Failed to load users. Please try again.</p>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-20">
            <UserCircleIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 mb-4">No CMS users found</p>
            <button
              onClick={() => setShowInviteModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Invite your first user
            </button>
          </div>
        ) : (
          <>
            {/* Table Header */}
            <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-white/10 text-xs font-medium text-white/50 uppercase tracking-wider">
              <div className="col-span-3">Name</div>
              <div className="col-span-3">Email</div>
              <div className="col-span-2">CMS Role</div>
              <div className="col-span-1">Status</div>
              <div className="col-span-2">Last Login</div>
              <div className="col-span-1 text-right">Actions</div>
            </div>

            {/* User Rows */}
            <div className="divide-y divide-white/5">
              {users.map((u) => {
                const roleBadge = getRoleBadge(u.cms_role);
                return (
                  <div
                    key={u.id}
                    className="grid grid-cols-1 md:grid-cols-12 gap-4 px-6 py-4 hover:bg-white/5 transition-colors items-center"
                  >
                    {/* Name */}
                    <div className="col-span-3 flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-500/30 to-cyan-500/30 flex items-center justify-center text-white font-medium text-sm flex-shrink-0">
                        {u.full_name?.charAt(0)?.toUpperCase() || 'U'}
                      </div>
                      <span className="text-white font-medium truncate">
                        {u.full_name || 'Unnamed'}
                      </span>
                    </div>

                    {/* Email */}
                    <div className="col-span-3 text-sm text-white/60 truncate">{u.email}</div>

                    {/* Role */}
                    <div className="col-span-2">
                      <select
                        value={u.cms_role}
                        onChange={(e) =>
                          updateRoleMutation.mutate({
                            userId: u.id,
                            role: e.target.value as CMSRole,
                          })
                        }
                        className={`text-xs font-medium px-2.5 py-1 rounded-full border-0 appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-purple-500/50 ${roleBadge.color}`}
                      >
                        {CMS_ROLES.map((r) => (
                          <option key={r.value} value={r.value} className="bg-neutral-900 text-white">
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Status */}
                    <div className="col-span-1">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          u.is_active
                            ? 'bg-green-500/10 text-green-400'
                            : 'bg-red-500/10 text-red-400'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    {/* Last Login */}
                    <div className="col-span-2 text-sm text-white/50">
                      {formatDate(u.last_login_at)}
                    </div>

                    {/* Actions */}
                    <div className="col-span-1 flex items-center justify-end">
                      <button
                        onClick={() => setRevokeConfirm(u.id)}
                        className="px-3 py-1 text-xs font-medium text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      >
                        Revoke
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* ── Invite User Modal ─────────────────────────────────────────────── */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Invite CMS User</h3>
              <button
                onClick={() => {
                  setShowInviteModal(false);
                  setInviteError(null);
                }}
                className="p-1 text-white/40 hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            {inviteError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
                {inviteError}
              </div>
            )}

            <form onSubmit={handleInviteSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={inviteForm.full_name}
                  onChange={(e) =>
                    setInviteForm((f) => ({ ...f, full_name: e.target.value }))
                  }
                  placeholder="Jane Smith"
                  required
                  className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) =>
                    setInviteForm((f) => ({ ...f, email: e.target.value }))
                  }
                  placeholder="jane@company.com"
                  required
                  className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={inviteForm.password}
                  onChange={(e) =>
                    setInviteForm((f) => ({ ...f, password: e.target.value }))
                  }
                  placeholder="Temporary password"
                  required
                  className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">
                  CMS Role
                </label>
                <select
                  value={inviteForm.cms_role}
                  onChange={(e) =>
                    setInviteForm((f) => ({ ...f, cms_role: e.target.value as CMSRole }))
                  }
                  className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white appearance-none focus:outline-none focus:border-purple-500/50"
                >
                  {CMS_ROLES.map((r) => (
                    <option key={r.value} value={r.value} className="bg-neutral-900">
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowInviteModal(false);
                    setInviteError(null);
                  }}
                  className="px-4 py-2 text-white/60 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviteMutation.isPending}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {inviteMutation.isPending ? 'Inviting...' : 'Invite User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Revoke Confirmation Modal ─────────────────────────────────────── */}
      {revokeConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-2">Revoke CMS Access</h3>
            <p className="text-white/60 mb-6">
              Are you sure you want to revoke this user's CMS access? They will no longer be
              able to log in to the CMS.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setRevokeConfirm(null)}
                className="px-4 py-2 text-white/60 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => revokeMutation.mutate(revokeConfirm)}
                disabled={revokeMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {revokeMutation.isPending ? 'Revoking...' : 'Revoke Access'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
