/**
 * CMS Permissions Hook
 * Fetches and caches the current user's CMS permissions.
 * Uses the CMS_PERMISSIONS matrix from the backend.
 */

import { useAuth } from '@/contexts/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export interface CMSPermissions {
  create_post: boolean;
  edit_own_post: boolean;
  edit_any_post: boolean;
  delete_any_post: boolean;
  publish_post: boolean;
  schedule_post: boolean;
  submit_for_review: boolean;
  approve_post: boolean;
  reject_post: boolean;
  request_changes: boolean;
  view_all_posts: boolean;
  view_own_posts: boolean;
  manage_categories: boolean;
  manage_tags: boolean;
  manage_authors: boolean;
  manage_pages: boolean;
  manage_users: boolean;
  view_analytics: boolean;
  export_content: boolean;
  bulk_operations: boolean;
  access_settings: boolean;
}

const emptyPermissions: CMSPermissions = {
  create_post: false,
  edit_own_post: false,
  edit_any_post: false,
  delete_any_post: false,
  publish_post: false,
  schedule_post: false,
  submit_for_review: false,
  approve_post: false,
  reject_post: false,
  request_changes: false,
  view_all_posts: false,
  view_own_posts: false,
  manage_categories: false,
  manage_tags: false,
  manage_authors: false,
  manage_pages: false,
  manage_users: false,
  view_analytics: false,
  export_content: false,
  bulk_operations: false,
  access_settings: false,
};

export function useCMSPermissions() {
  const { user } = useAuth();
  const cmsRole = user?.cms_role;

  const { data: permissionsData } = useQuery({
    queryKey: ['cms-permissions', cmsRole],
    queryFn: async () => {
      if (!cmsRole) return null;
      try {
        const res = await apiClient.get('/cms/admin/me/permissions');
        return res.data?.data?.permissions || null;
      } catch {
        return null;
      }
    },
    enabled: !!cmsRole,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const permissions: CMSPermissions = permissionsData || emptyPermissions;

  const hasPermission = (perm: keyof CMSPermissions): boolean => {
    return permissions[perm] ?? false;
  };

  return { cmsRole, permissions, hasPermission };
}
