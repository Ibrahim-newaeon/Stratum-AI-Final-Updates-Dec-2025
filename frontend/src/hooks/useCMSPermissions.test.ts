/**
 * useCMSPermissions Hook Tests
 *
 * Tests for the CMS permissions hook that fetches and caches
 * the current user's CMS role-based permissions.
 * Mocks AuthContext, React Query, and the API client.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock dependencies
// ---------------------------------------------------------------------------

let mockUser: any = null;
let mockQueryResult: any = { data: null };

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser }),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: (options: any) => {
    // Simulate the enabled check
    if (options.enabled === false) {
      return { data: undefined };
    }
    return { data: mockQueryResult.data };
  },
}));

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { useCMSPermissions, type CMSPermissions } from './useCMSPermissions';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const fullPermissions: CMSPermissions = {
  create_post: true,
  edit_own_post: true,
  edit_any_post: true,
  delete_any_post: true,
  publish_post: true,
  schedule_post: true,
  submit_for_review: true,
  approve_post: true,
  reject_post: true,
  request_changes: true,
  view_all_posts: true,
  view_own_posts: true,
  manage_categories: true,
  manage_tags: true,
  manage_authors: true,
  manage_pages: true,
  manage_users: true,
  view_analytics: true,
  export_content: true,
  bulk_operations: true,
  access_settings: true,
};

const editorPermissions: CMSPermissions = {
  create_post: true,
  edit_own_post: true,
  edit_any_post: false,
  delete_any_post: false,
  publish_post: false,
  schedule_post: true,
  submit_for_review: true,
  approve_post: false,
  reject_post: false,
  request_changes: false,
  view_all_posts: false,
  view_own_posts: true,
  manage_categories: false,
  manage_tags: true,
  manage_authors: false,
  manage_pages: false,
  manage_users: false,
  view_analytics: false,
  export_content: false,
  bulk_operations: false,
  access_settings: false,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useCMSPermissions', () => {
  beforeEach(() => {
    mockUser = null;
    mockQueryResult = { data: null };
  });

  // -------------------------------------------------------------------------
  // No user / no CMS role
  // -------------------------------------------------------------------------

  describe('No User / No CMS Role', () => {
    it('should return empty permissions when user is null', () => {
      mockUser = null;
      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.cmsRole).toBeUndefined();
      expect(result.current.permissions.create_post).toBe(false);
      expect(result.current.permissions.publish_post).toBe(false);
    });

    it('should return empty permissions when user has no cms_role', () => {
      mockUser = { id: 1, email: 'test@test.com' };
      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.cmsRole).toBeUndefined();
      expect(result.current.permissions.create_post).toBe(false);
    });

    it('should have all permissions set to false by default', () => {
      mockUser = null;
      const { result } = renderHook(() => useCMSPermissions());

      const allFalse = Object.values(result.current.permissions).every((v) => v === false);
      expect(allFalse).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // With CMS role and permissions data
  // -------------------------------------------------------------------------

  describe('With CMS Role', () => {
    it('should return full permissions for admin role', () => {
      mockUser = { id: 1, email: 'admin@test.com', cms_role: 'admin' };
      mockQueryResult = { data: fullPermissions };

      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.cmsRole).toBe('admin');
      expect(result.current.permissions.create_post).toBe(true);
      expect(result.current.permissions.manage_users).toBe(true);
      expect(result.current.permissions.delete_any_post).toBe(true);
    });

    it('should return partial permissions for editor role', () => {
      mockUser = { id: 2, email: 'editor@test.com', cms_role: 'editor' };
      mockQueryResult = { data: editorPermissions };

      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.cmsRole).toBe('editor');
      expect(result.current.permissions.create_post).toBe(true);
      expect(result.current.permissions.edit_own_post).toBe(true);
      expect(result.current.permissions.edit_any_post).toBe(false);
      expect(result.current.permissions.manage_users).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // hasPermission method
  // -------------------------------------------------------------------------

  describe('hasPermission', () => {
    it('should return true for granted permissions', () => {
      mockUser = { id: 1, email: 'admin@test.com', cms_role: 'admin' };
      mockQueryResult = { data: fullPermissions };

      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.hasPermission('create_post')).toBe(true);
      expect(result.current.hasPermission('delete_any_post')).toBe(true);
      expect(result.current.hasPermission('manage_users')).toBe(true);
    });

    it('should return false for denied permissions', () => {
      mockUser = { id: 2, email: 'editor@test.com', cms_role: 'editor' };
      mockQueryResult = { data: editorPermissions };

      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.hasPermission('edit_any_post')).toBe(false);
      expect(result.current.hasPermission('manage_users')).toBe(false);
      expect(result.current.hasPermission('delete_any_post')).toBe(false);
    });

    it('should return false when no permissions data is loaded', () => {
      mockUser = null;
      mockQueryResult = { data: null };

      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.hasPermission('create_post')).toBe(false);
      expect(result.current.hasPermission('publish_post')).toBe(false);
    });

    it('should check each permission key correctly', () => {
      mockUser = { id: 1, cms_role: 'editor' };
      mockQueryResult = { data: editorPermissions };

      const { result } = renderHook(() => useCMSPermissions());

      // Verify a mix of granted and denied
      expect(result.current.hasPermission('create_post')).toBe(true);
      expect(result.current.hasPermission('submit_for_review')).toBe(true);
      expect(result.current.hasPermission('view_own_posts')).toBe(true);
      expect(result.current.hasPermission('approve_post')).toBe(false);
      expect(result.current.hasPermission('access_settings')).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // cmsRole exposure
  // -------------------------------------------------------------------------

  describe('cmsRole', () => {
    it('should expose the user CMS role', () => {
      mockUser = { id: 1, cms_role: 'contributor' };
      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.cmsRole).toBe('contributor');
    });

    it('should be undefined when user has no CMS role', () => {
      mockUser = { id: 1 };
      const { result } = renderHook(() => useCMSPermissions());

      expect(result.current.cmsRole).toBeUndefined();
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  describe('Edge Cases', () => {
    it('should handle API returning null permissions gracefully', () => {
      mockUser = { id: 1, cms_role: 'admin' };
      mockQueryResult = { data: null };

      const { result } = renderHook(() => useCMSPermissions());

      // Falls back to emptyPermissions
      expect(result.current.permissions.create_post).toBe(false);
      expect(result.current.hasPermission('create_post')).toBe(false);
    });

    it('should return a stable permissions object structure', () => {
      mockUser = null;
      const { result } = renderHook(() => useCMSPermissions());

      const permKeys = Object.keys(result.current.permissions);
      expect(permKeys).toContain('create_post');
      expect(permKeys).toContain('edit_own_post');
      expect(permKeys).toContain('manage_users');
      expect(permKeys).toContain('access_settings');
      expect(permKeys).toHaveLength(21);
    });
  });
});
