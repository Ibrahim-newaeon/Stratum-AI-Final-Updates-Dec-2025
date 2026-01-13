/**
 * Stratum AI - Team Management Page
 *
 * Manage team members and their access to the tenant.
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTenantUsers, useCreateUser, useUpdateUser, useDeleteUser } from '@/api/admin'
import { useToast } from '@/components/ui/use-toast'
import {
  UserPlusIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  ArrowLeftIcon,
  ShieldCheckIcon,
  EnvelopeIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

interface TeamMember {
  id: number
  email: string
  name: string
  role: string
  isActive: boolean
  lastLoginAt: string | null
  createdAt: string
}

const ROLES = [
  { value: 'admin', label: 'Admin', description: 'Full access to all features' },
  { value: 'manager', label: 'Manager', description: 'Manage campaigns and team' },
  { value: 'analyst', label: 'Analyst', description: 'View reports and analytics' },
  { value: 'viewer', label: 'Viewer', description: 'Read-only access' },
]

export default function TeamManagement() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const tenantIdNum = tenantId ? parseInt(tenantId, 10) : 0

  const { data: usersData, isLoading, refetch } = useTenantUsers(tenantIdNum)
  const createUserMutation = useCreateUser()
  const updateUserMutation = useUpdateUser()
  const deleteUserMutation = useDeleteUser()

  const [searchQuery, setSearchQuery] = useState('')
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<TeamMember | null>(null)
  const [newUser, setNewUser] = useState({
    email: '',
    name: '',
    role: 'viewer',
  })

  const users: TeamMember[] = usersData || []

  const filteredUsers = users.filter(
    (user) =>
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleInvite = async () => {
    if (!newUser.email) {
      toast({
        title: 'Error',
        description: 'Email is required',
        variant: 'destructive',
      })
      return
    }

    try {
      // Generate a temporary password for invite flow - user will reset via email
      const tempPassword = `Temp${Math.random().toString(36).slice(-8)}!`
      await createUserMutation.mutateAsync({
        tenantId: tenantIdNum,
        email: newUser.email,
        name: newUser.name || newUser.email.split('@')[0],
        password: tempPassword,
        role: newUser.role as 'superadmin' | 'admin' | 'user' | 'viewer',
      })
      toast({
        title: 'Success',
        description: 'Team member invited successfully',
      })
      setShowInviteModal(false)
      setNewUser({ email: '', name: '', role: 'viewer' })
      refetch()
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to invite team member',
        variant: 'destructive',
      })
    }
  }

  const handleUpdateRole = async (userId: number, newRole: string) => {
    try {
      await updateUserMutation.mutateAsync({
        id: userId,
        data: { role: newRole as 'superadmin' | 'admin' | 'user' | 'viewer' },
      })
      toast({
        title: 'Success',
        description: 'Role updated successfully',
      })
      refetch()
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to update role',
        variant: 'destructive',
      })
    }
  }

  const handleRemoveUser = async (userId: number, userName: string) => {
    if (!confirm(`Are you sure you want to remove ${userName} from the team?`)) {
      return
    }

    try {
      await deleteUserMutation.mutateAsync(userId)
      toast({
        title: 'Success',
        description: 'Team member removed successfully',
      })
      refetch()
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to remove team member',
        variant: 'destructive',
      })
    }
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
      case 'manager':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
      case 'analyst':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/app/${tenantId}/settings`)}
            className="p-2 rounded-lg hover:bg-accent transition-colors"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">Team Management</h1>
            <p className="text-muted-foreground">
              Manage team members and their access permissions
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
        >
          <UserPlusIcon className="h-5 w-5" />
          Invite Member
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search team members..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>

      {/* Team Members Table */}
      <div className="rounded-xl border bg-card shadow-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                Member
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                Role
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                Status
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-muted-foreground">
                Last Login
              </th>
              <th className="text-right px-6 py-3 text-sm font-medium text-muted-foreground">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">
                  {searchQuery ? 'No team members found matching your search.' : 'No team members yet. Invite your first team member!'}
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-muted/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="text-sm font-medium text-primary">
                          {user.name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium">{user.name || 'No name'}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <select
                      value={user.role}
                      onChange={(e) => handleUpdateRole(user.id, e.target.value)}
                      className={cn(
                        'px-3 py-1 rounded-full text-xs font-medium border-0 cursor-pointer',
                        getRoleBadgeColor(user.role)
                      )}
                    >
                      {ROLES.map((role) => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {user.isActive ? (
                        <>
                          <CheckCircleIcon className="h-5 w-5 text-green-500" />
                          <span className="text-sm text-green-600 dark:text-green-400">Active</span>
                        </>
                      ) : (
                        <>
                          <XCircleIcon className="h-5 w-5 text-red-500" />
                          <span className="text-sm text-red-600 dark:text-red-400">Inactive</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {formatDate(user.lastLoginAt)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => {
                          setSelectedUser(user)
                          setShowEditModal(true)
                        }}
                        className="p-2 rounded-lg hover:bg-accent transition-colors"
                        title="Edit member"
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleRemoveUser(user.id, user.name || user.email)}
                        className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition-colors"
                        title="Remove member"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Role Legend */}
      <div className="rounded-xl border bg-card p-6 shadow-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <ShieldCheckIcon className="h-5 w-5" />
          Role Permissions
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {ROLES.map((role) => (
            <div key={role.value} className="p-4 rounded-lg bg-muted/50">
              <span className={cn('px-2 py-1 rounded-full text-xs font-medium', getRoleBadgeColor(role.value))}>
                {role.label}
              </span>
              <p className="text-sm text-muted-foreground mt-2">{role.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowInviteModal(false)}
          />
          <div className="relative z-10 w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
            <h2 className="text-lg font-semibold mb-4">Invite Team Member</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Email Address</label>
                <div className="relative">
                  <EnvelopeIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                    placeholder="email@example.com"
                    className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  value={newUser.name}
                  onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                  placeholder="John Doe"
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  {ROLES.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label} - {role.description}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowInviteModal(false)}
                className="px-4 py-2 rounded-lg border hover:bg-accent transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleInvite}
                disabled={createUserMutation.isPending}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {createUserMutation.isPending ? 'Inviting...' : 'Send Invite'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowEditModal(false)}
          />
          <div className="relative z-10 w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
            <h2 className="text-lg font-semibold mb-4">Edit Team Member</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Email Address</label>
                <input
                  type="email"
                  value={selectedUser.email}
                  disabled
                  className="w-full px-4 py-2 rounded-lg border bg-muted cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  value={selectedUser.name || ''}
                  onChange={(e) =>
                    setSelectedUser({ ...selectedUser, name: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Role</label>
                <select
                  value={selectedUser.role}
                  onChange={(e) =>
                    setSelectedUser({ ...selectedUser, role: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  {ROLES.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label} - {role.description}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 rounded-lg border hover:bg-accent transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await handleUpdateRole(selectedUser.id, selectedUser.role)
                  setShowEditModal(false)
                }}
                disabled={updateUserMutation.isPending}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {updateUserMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
