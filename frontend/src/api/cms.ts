/**
 * Stratum AI - CMS (Content Management System) API Client
 *
 * API client with TypeScript types and React Query hooks for CMS endpoints.
 * Handles blog posts, pages, categories, tags, authors, and contact submissions.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// TypeScript Types
// =============================================================================

// Status Types
export type PostStatus = 'draft' | 'scheduled' | 'published' | 'archived'
export type ContentType = 'blog_post' | 'case_study' | 'guide' | 'whitepaper' | 'announcement'
export type PageStatus = 'draft' | 'published' | 'archived'

// Category Types
export interface CMSCategory {
  id: string
  name: string
  slug: string
  description?: string
  color?: string
  icon?: string
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CategoryCreate {
  name: string
  slug?: string
  description?: string
  color?: string
  icon?: string
  display_order?: number
  is_active?: boolean
}

export interface CategoryUpdate {
  name?: string
  slug?: string
  description?: string
  color?: string
  icon?: string
  display_order?: number
  is_active?: boolean
}

export interface CategoryListResponse {
  categories: CMSCategory[]
  total: number
}

// Tag Types
export interface CMSTag {
  id: string
  name: string
  slug: string
  description?: string
  color?: string
  usage_count: number
  created_at: string
  updated_at: string
}

export interface TagCreate {
  name: string
  slug?: string
  description?: string
  color?: string
}

export interface TagUpdate {
  name?: string
  slug?: string
  description?: string
  color?: string
}

export interface TagListResponse {
  tags: CMSTag[]
  total: number
}

// Author Types
export interface CMSAuthor {
  id: string
  user_id?: number
  name: string
  slug: string
  email?: string
  bio?: string
  avatar_url?: string
  job_title?: string
  company?: string
  twitter_handle?: string
  linkedin_url?: string
  github_handle?: string
  website_url?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthorCreate {
  name: string
  slug?: string
  email?: string
  bio?: string
  avatar_url?: string
  job_title?: string
  company?: string
  twitter_handle?: string
  linkedin_url?: string
  github_handle?: string
  website_url?: string
  user_id?: number
  is_active?: boolean
}

export interface AuthorUpdate {
  name?: string
  slug?: string
  email?: string
  bio?: string
  avatar_url?: string
  job_title?: string
  company?: string
  twitter_handle?: string
  linkedin_url?: string
  github_handle?: string
  website_url?: string
  user_id?: number
  is_active?: boolean
}

export interface AuthorListResponse {
  authors: CMSAuthor[]
  total: number
}

// Post Types
export interface CMSPost {
  id: string
  title: string
  slug: string
  excerpt?: string
  content?: string
  content_json?: Record<string, unknown>
  status: PostStatus
  content_type: ContentType
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  word_count?: number
  view_count: number
  is_featured: boolean
  allow_comments: boolean
  category?: CMSCategory
  author?: CMSAuthor
  tags: CMSTag[]
  created_at: string
  updated_at: string
}

export interface PostPublic {
  id: string
  title: string
  slug: string
  excerpt?: string
  content?: string
  published_at?: string
  meta_title?: string
  meta_description?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  view_count: number
  is_featured: boolean
  content_type: ContentType
  category?: CMSCategory
  author?: CMSAuthor
  tags: CMSTag[]
}

export interface PostCreate {
  title: string
  slug?: string
  excerpt?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PostStatus
  content_type?: ContentType
  category_id?: string
  author_id?: string
  tag_ids?: string[]
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  is_featured?: boolean
  allow_comments?: boolean
}

export interface PostUpdate {
  title?: string
  slug?: string
  excerpt?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PostStatus
  content_type?: ContentType
  category_id?: string
  author_id?: string
  tag_ids?: string[]
  published_at?: string
  scheduled_at?: string
  meta_title?: string
  meta_description?: string
  canonical_url?: string
  og_image_url?: string
  featured_image_url?: string
  featured_image_alt?: string
  reading_time_minutes?: number
  is_featured?: boolean
  allow_comments?: boolean
}

export interface PostListResponse {
  posts: CMSPost[]
  total: number
  page: number
  page_size: number
}

export interface PostPublicListResponse {
  posts: PostPublic[]
  total: number
  page: number
  page_size: number
}

// Page Types
export interface CMSPage {
  id: string
  title: string
  slug: string
  content?: string
  content_json?: Record<string, unknown>
  status: PageStatus
  published_at?: string
  meta_title?: string
  meta_description?: string
  show_in_navigation: boolean
  navigation_label?: string
  navigation_order: number
  template: string
  created_at: string
  updated_at: string
}

export interface PageCreate {
  title: string
  slug?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PageStatus
  meta_title?: string
  meta_description?: string
  show_in_navigation?: boolean
  navigation_label?: string
  navigation_order?: number
  template?: string
}

export interface PageUpdate {
  title?: string
  slug?: string
  content?: string
  content_json?: Record<string, unknown>
  status?: PageStatus
  meta_title?: string
  meta_description?: string
  show_in_navigation?: boolean
  navigation_label?: string
  navigation_order?: number
  template?: string
}

export interface PageListResponse {
  pages: CMSPage[]
  total: number
}

// Contact Types
export interface CMSContact {
  id: string
  name: string
  email: string
  company?: string
  phone?: string
  subject?: string
  message: string
  source_page?: string
  is_read: boolean
  read_at?: string
  is_responded: boolean
  responded_at?: string
  response_notes?: string
  is_spam: boolean
  created_at: string
}

export interface ContactSubmit {
  name: string
  email: string
  company?: string
  phone?: string
  subject?: string
  message: string
  source_page?: string
}

export interface ContactListResponse {
  contacts: CMSContact[]
  total: number
  page: number
  page_size: number
}

// Filter Types
export interface PostFilters {
  page?: number
  page_size?: number
  category_slug?: string
  tag_slug?: string
  content_type?: ContentType
  search?: string
  featured_only?: boolean
}

export interface AdminPostFilters extends PostFilters {
  status_filter?: PostStatus
}

export interface ContactFilters {
  page?: number
  page_size?: number
  unread_only?: boolean
  exclude_spam?: boolean
}

// =============================================================================
// Query Keys
// =============================================================================

export const cmsKeys = {
  all: ['cms'] as const,
  // Posts
  posts: () => [...cmsKeys.all, 'posts'] as const,
  postsList: (filters: PostFilters) => [...cmsKeys.posts(), 'list', filters] as const,
  postsDetail: (slug: string) => [...cmsKeys.posts(), 'detail', slug] as const,
  postsAdmin: (filters: AdminPostFilters) => [...cmsKeys.posts(), 'admin', filters] as const,
  postsAdminDetail: (id: string) => [...cmsKeys.posts(), 'admin', 'detail', id] as const,
  // Categories
  categories: () => [...cmsKeys.all, 'categories'] as const,
  categoriesList: (activeOnly?: boolean) => [...cmsKeys.categories(), { activeOnly }] as const,
  // Tags
  tags: () => [...cmsKeys.all, 'tags'] as const,
  tagsList: () => [...cmsKeys.tags(), 'list'] as const,
  // Authors
  authors: () => [...cmsKeys.all, 'authors'] as const,
  authorsList: () => [...cmsKeys.authors(), 'list'] as const,
  // Pages
  pages: () => [...cmsKeys.all, 'pages'] as const,
  pagesList: () => [...cmsKeys.pages(), 'list'] as const,
  // Contacts
  contacts: () => [...cmsKeys.all, 'contacts'] as const,
  contactsList: (filters: ContactFilters) => [...cmsKeys.contacts(), 'list', filters] as const,
}

// =============================================================================
// Public API Functions
// =============================================================================

// Posts (Public)
export const fetchPublishedPosts = async (filters: PostFilters = {}): Promise<PostPublicListResponse> => {
  const params = new URLSearchParams()
  if (filters.page) params.append('page', String(filters.page))
  if (filters.page_size) params.append('page_size', String(filters.page_size))
  if (filters.category_slug) params.append('category_slug', filters.category_slug)
  if (filters.tag_slug) params.append('tag_slug', filters.tag_slug)
  if (filters.content_type) params.append('content_type', filters.content_type)
  if (filters.search) params.append('search', filters.search)
  if (filters.featured_only) params.append('featured_only', 'true')

  const response = await apiClient.get<ApiResponse<PostPublicListResponse>>(
    `/cms/posts?${params.toString()}`
  )
  return response.data.data
}

export const fetchPostBySlug = async (slug: string): Promise<PostPublic> => {
  const response = await apiClient.get<ApiResponse<PostPublic>>(`/cms/posts/${slug}`)
  return response.data.data
}

// Categories (Public)
export const fetchCategories = async (activeOnly = true): Promise<CategoryListResponse> => {
  const response = await apiClient.get<ApiResponse<CategoryListResponse>>(
    `/cms/categories?active_only=${activeOnly}`
  )
  return response.data.data
}

// Tags (Public)
export const fetchTags = async (): Promise<TagListResponse> => {
  const response = await apiClient.get<ApiResponse<TagListResponse>>('/cms/tags')
  return response.data.data
}

// Contact Form (Public)
export const submitContactForm = async (data: ContactSubmit): Promise<{ submitted: boolean }> => {
  const response = await apiClient.post<ApiResponse<{ submitted: boolean }>>('/cms/contact', data)
  return response.data.data
}

// =============================================================================
// Admin API Functions
// =============================================================================

// Admin Posts
export const fetchAdminPosts = async (filters: AdminPostFilters = {}): Promise<PostListResponse> => {
  const params = new URLSearchParams()
  if (filters.page) params.append('page', String(filters.page))
  if (filters.page_size) params.append('page_size', String(filters.page_size))
  if (filters.status_filter) params.append('status_filter', filters.status_filter)
  if (filters.content_type) params.append('content_type', filters.content_type)
  if (filters.search) params.append('search', filters.search)

  const response = await apiClient.get<ApiResponse<PostListResponse>>(
    `/cms/admin/posts?${params.toString()}`
  )
  return response.data.data
}

export const fetchAdminPost = async (id: string): Promise<CMSPost> => {
  const response = await apiClient.get<ApiResponse<CMSPost>>(`/cms/admin/posts/${id}`)
  return response.data.data
}

export const createPost = async (data: PostCreate): Promise<CMSPost> => {
  const response = await apiClient.post<ApiResponse<CMSPost>>('/cms/admin/posts', data)
  return response.data.data
}

export const updatePost = async (id: string, data: PostUpdate): Promise<CMSPost> => {
  const response = await apiClient.patch<ApiResponse<CMSPost>>(`/cms/admin/posts/${id}`, data)
  return response.data.data
}

export const deletePost = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/posts/${id}`)
}

// Admin Categories
export const fetchAdminCategories = async (): Promise<CategoryListResponse> => {
  const response = await apiClient.get<ApiResponse<CategoryListResponse>>('/cms/admin/categories')
  return response.data.data
}

export const createCategory = async (data: CategoryCreate): Promise<CMSCategory> => {
  const response = await apiClient.post<ApiResponse<CMSCategory>>('/cms/admin/categories', data)
  return response.data.data
}

export const updateCategory = async (id: string, data: CategoryUpdate): Promise<CMSCategory> => {
  const response = await apiClient.patch<ApiResponse<CMSCategory>>(`/cms/admin/categories/${id}`, data)
  return response.data.data
}

export const deleteCategory = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/categories/${id}`)
}

// Admin Tags
export const fetchAdminTags = async (): Promise<TagListResponse> => {
  const response = await apiClient.get<ApiResponse<TagListResponse>>('/cms/admin/tags')
  return response.data.data
}

export const createTag = async (data: TagCreate): Promise<CMSTag> => {
  const response = await apiClient.post<ApiResponse<CMSTag>>('/cms/admin/tags', data)
  return response.data.data
}

export const updateTag = async (id: string, data: TagUpdate): Promise<CMSTag> => {
  const response = await apiClient.patch<ApiResponse<CMSTag>>(`/cms/admin/tags/${id}`, data)
  return response.data.data
}

export const deleteTag = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/tags/${id}`)
}

// Admin Authors
export const fetchAdminAuthors = async (): Promise<AuthorListResponse> => {
  const response = await apiClient.get<ApiResponse<AuthorListResponse>>('/cms/admin/authors')
  return response.data.data
}

export const createAuthor = async (data: AuthorCreate): Promise<CMSAuthor> => {
  const response = await apiClient.post<ApiResponse<CMSAuthor>>('/cms/admin/authors', data)
  return response.data.data
}

export const updateAuthor = async (id: string, data: AuthorUpdate): Promise<CMSAuthor> => {
  const response = await apiClient.patch<ApiResponse<CMSAuthor>>(`/cms/admin/authors/${id}`, data)
  return response.data.data
}

export const deleteAuthor = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/authors/${id}`)
}

// Admin Pages
export const fetchAdminPages = async (): Promise<PageListResponse> => {
  const response = await apiClient.get<ApiResponse<PageListResponse>>('/cms/admin/pages')
  return response.data.data
}

export const createPage = async (data: PageCreate): Promise<CMSPage> => {
  const response = await apiClient.post<ApiResponse<CMSPage>>('/cms/admin/pages', data)
  return response.data.data
}

export const updatePage = async (id: string, data: PageUpdate): Promise<CMSPage> => {
  const response = await apiClient.patch<ApiResponse<CMSPage>>(`/cms/admin/pages/${id}`, data)
  return response.data.data
}

export const deletePage = async (id: string): Promise<void> => {
  await apiClient.delete(`/cms/admin/pages/${id}`)
}

// Admin Contacts
export const fetchAdminContacts = async (filters: ContactFilters = {}): Promise<ContactListResponse> => {
  const params = new URLSearchParams()
  if (filters.page) params.append('page', String(filters.page))
  if (filters.page_size) params.append('page_size', String(filters.page_size))
  if (filters.unread_only) params.append('unread_only', 'true')
  if (filters.exclude_spam !== undefined) params.append('exclude_spam', String(filters.exclude_spam))

  const response = await apiClient.get<ApiResponse<ContactListResponse>>(
    `/cms/admin/contacts?${params.toString()}`
  )
  return response.data.data
}

export const markContactRead = async (id: string, isRead: boolean): Promise<CMSContact> => {
  const response = await apiClient.patch<ApiResponse<CMSContact>>(
    `/cms/admin/contacts/${id}/read`,
    { is_read: isRead }
  )
  return response.data.data
}

export const markContactResponded = async (
  id: string,
  isResponded: boolean,
  responseNotes?: string
): Promise<CMSContact> => {
  const response = await apiClient.patch<ApiResponse<CMSContact>>(
    `/cms/admin/contacts/${id}/responded`,
    { is_responded: isResponded, response_notes: responseNotes }
  )
  return response.data.data
}

export const markContactSpam = async (id: string, isSpam: boolean): Promise<CMSContact> => {
  const response = await apiClient.patch<ApiResponse<CMSContact>>(
    `/cms/admin/contacts/${id}/spam`,
    { is_spam: isSpam }
  )
  return response.data.data
}

// =============================================================================
// React Query Hooks - Public
// =============================================================================

export const usePosts = (filters: PostFilters = {}) => {
  return useQuery({
    queryKey: cmsKeys.postsList(filters),
    queryFn: () => fetchPublishedPosts(filters),
  })
}

export const usePost = (slug: string) => {
  return useQuery({
    queryKey: cmsKeys.postsDetail(slug),
    queryFn: () => fetchPostBySlug(slug),
    enabled: !!slug,
  })
}

export const useCategories = (activeOnly = true) => {
  return useQuery({
    queryKey: cmsKeys.categoriesList(activeOnly),
    queryFn: () => fetchCategories(activeOnly),
  })
}

export const useTags = () => {
  return useQuery({
    queryKey: cmsKeys.tagsList(),
    queryFn: fetchTags,
  })
}

export const useSubmitContact = () => {
  return useMutation({
    mutationFn: submitContactForm,
  })
}

// =============================================================================
// React Query Hooks - Admin Posts
// =============================================================================

export const useAdminPosts = (filters: AdminPostFilters = {}) => {
  return useQuery({
    queryKey: cmsKeys.postsAdmin(filters),
    queryFn: () => fetchAdminPosts(filters),
  })
}

export const useAdminPost = (id: string) => {
  return useQuery({
    queryKey: cmsKeys.postsAdminDetail(id),
    queryFn: () => fetchAdminPost(id),
    enabled: !!id,
  })
}

export const useCreatePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useUpdatePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PostUpdate }) => updatePost(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

export const useDeletePost = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deletePost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.posts() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Categories
// =============================================================================

export const useAdminCategories = () => {
  return useQuery({
    queryKey: cmsKeys.categories(),
    queryFn: fetchAdminCategories,
  })
}

export const useCreateCategory = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.categories() })
    },
  })
}

export const useUpdateCategory = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CategoryUpdate }) => updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.categories() })
    },
  })
}

export const useDeleteCategory = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.categories() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Tags
// =============================================================================

export const useAdminTags = () => {
  return useQuery({
    queryKey: cmsKeys.tags(),
    queryFn: fetchAdminTags,
  })
}

export const useCreateTag = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.tags() })
    },
  })
}

export const useUpdateTag = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TagUpdate }) => updateTag(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.tags() })
    },
  })
}

export const useDeleteTag = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.tags() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Authors
// =============================================================================

export const useAdminAuthors = () => {
  return useQuery({
    queryKey: cmsKeys.authors(),
    queryFn: fetchAdminAuthors,
  })
}

export const useCreateAuthor = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAuthor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.authors() })
    },
  })
}

export const useUpdateAuthor = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AuthorUpdate }) => updateAuthor(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.authors() })
    },
  })
}

export const useDeleteAuthor = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteAuthor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.authors() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Pages
// =============================================================================

export const useAdminPages = () => {
  return useQuery({
    queryKey: cmsKeys.pagesList(),
    queryFn: fetchAdminPages,
  })
}

export const useCreatePage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.pages() })
    },
  })
}

export const useUpdatePage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PageUpdate }) => updatePage(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.pages() })
    },
  })
}

export const useDeletePage = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deletePage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.pages() })
    },
  })
}

// =============================================================================
// React Query Hooks - Admin Contacts
// =============================================================================

export const useAdminContacts = (filters: ContactFilters = {}) => {
  return useQuery({
    queryKey: cmsKeys.contactsList(filters),
    queryFn: () => fetchAdminContacts(filters),
  })
}

export const useMarkContactRead = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isRead }: { id: string; isRead: boolean }) => markContactRead(id, isRead),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.contacts() })
    },
  })
}

export const useMarkContactResponded = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isResponded, responseNotes }: { id: string; isResponded: boolean; responseNotes?: string }) =>
      markContactResponded(id, isResponded, responseNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.contacts() })
    },
  })
}

export const useMarkContactSpam = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, isSpam }: { id: string; isSpam: boolean }) => markContactSpam(id, isSpam),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cmsKeys.contacts() })
    },
  })
}
