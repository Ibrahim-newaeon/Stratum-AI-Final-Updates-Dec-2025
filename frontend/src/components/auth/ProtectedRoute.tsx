/**
 * Protected Route Component
 * Wraps routes that require authentication
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import LoadingSpinner from '@/components/common/LoadingSpinner'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: 'superadmin' | 'admin' | 'user'
  requiredPermission?: string
}

export default function ProtectedRoute({
  children,
  requiredRole,
  requiredPermission,
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // Show loading while checking auth state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <LoadingSpinner />
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Check role permissions
  if (requiredRole && user) {
    const roleHierarchy = { superadmin: 3, admin: 2, user: 1 }
    const userLevel = roleHierarchy[user.role] || 0
    const requiredLevel = roleHierarchy[requiredRole] || 0

    if (userLevel < requiredLevel) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  // Check specific permission
  if (requiredPermission && user) {
    const hasPermission =
      user.permissions.includes('all') || user.permissions.includes(requiredPermission)
    if (!hasPermission) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return <>{children}</>
}
