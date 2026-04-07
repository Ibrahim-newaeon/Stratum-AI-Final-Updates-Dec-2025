/**
 * CMS Protected Route
 * Checks for cms_role instead of the platform role.
 * Redirects to /cms-login if user has no CMS access.
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

interface CMSProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
}

export default function CMSProtectedRoute({
  children,
  requiredPermission,
}: CMSProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/cms-login" state={{ from: location }} replace />;
  }

  // Must have a cms_role to access CMS
  if (!user.cms_role) {
    return <Navigate to="/cms-login" state={{ error: 'no-cms-access' }} replace />;
  }

  // Optional: check specific permission
  if (requiredPermission && user.cms_permissions) {
    if (!user.cms_permissions[requiredPermission]) {
      return <Navigate to="/cms" replace />;
    }
  }

  return <>{children}</>;
}
