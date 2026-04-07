/**
 * Stratum AI - Post Editor Component
 *
 * Full form for creating/editing blog posts with all fields including
 * title, content (TipTap), SEO settings, featured image, and metadata.
 */

import { useEffect, useState } from 'react';
import { Image as ImageIcon, Link2, Save, X } from 'lucide-react';
import { RichTextEditor } from './RichTextEditor';
import {
  CMSAuthor,
  CMSCategory,
  CMSPost,
  CMSTag,
  ContentType,
  PostCreate,
  PostStatus,
  PostUpdate,
} from '@/api/cms';

interface PostEditorProps {
  post?: CMSPost;
  categories: CMSCategory[];
  authors: CMSAuthor[];
  tags: CMSTag[];
  onSave: (data: PostCreate | PostUpdate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  inline?: boolean;
}

const statusOptions: { value: PostStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'published', label: 'Published' },
  { value: 'archived', label: 'Archived' },
];

const contentTypeOptions: { value: ContentType; label: string }[] = [
  { value: 'blog_post', label: 'Blog Post' },
  { value: 'case_study', label: 'Case Study' },
  { value: 'guide', label: 'Guide' },
  { value: 'whitepaper', label: 'Whitepaper' },
  { value: 'announcement', label: 'Announcement' },
];

export function PostEditor({
  post,
  categories,
  authors,
  tags,
  onSave,
  onCancel,
  isLoading = false,
  inline = false,
}: PostEditorProps) {
  const [formData, setFormData] = useState<PostCreate>({
    title: '',
    slug: '',
    excerpt: '',
    content: '',
    content_json: undefined,
    status: 'draft',
    content_type: 'blog_post',
    category_id: undefined,
    author_id: undefined,
    tag_ids: [],
    meta_title: '',
    meta_description: '',
    featured_image_url: '',
    featured_image_alt: '',
    og_image_url: '',
    canonical_url: '',
    is_featured: false,
    allow_comments: true,
  });

  const [activeTab, setActiveTab] = useState<'content' | 'seo' | 'settings'>('content');

  // Initialize form with existing post data
  useEffect(() => {
    if (post) {
      setFormData({
        title: post.title,
        slug: post.slug,
        excerpt: post.excerpt || '',
        content: post.content || '',
        content_json: post.content_json,
        status: post.status,
        content_type: post.content_type,
        category_id: post.category?.id,
        author_id: post.author?.id,
        tag_ids: post.tags.map((t) => t.id),
        meta_title: post.meta_title || '',
        meta_description: post.meta_description || '',
        featured_image_url: post.featured_image_url || '',
        featured_image_alt: post.featured_image_alt || '',
        og_image_url: post.og_image_url || '',
        canonical_url: post.canonical_url || '',
        is_featured: post.is_featured,
        allow_comments: post.allow_comments,
      });
    }
  }, [post]);

  // Auto-generate slug from title
  const generateSlug = (title: string) => {
    return title
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[-\s]+/g, '-');
  };

  const handleTitleChange = (title: string) => {
    setFormData((prev) => ({
      ...prev,
      title,
      slug: prev.slug || generateSlug(title),
    }));
  };

  const handleContentChange = (html: string, json: Record<string, unknown>) => {
    setFormData((prev) => ({
      ...prev,
      content: html,
      content_json: json,
    }));
  };

  const handleTagToggle = (tagId: string) => {
    setFormData((prev) => ({
      ...prev,
      tag_ids: prev.tag_ids?.includes(tagId)
        ? prev.tag_ids.filter((id) => id !== tagId)
        : [...(prev.tag_ids || []), tagId],
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const wrapperClass = inline
    ? ''
    : 'fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4';
  const containerClass = inline
    ? 'bg-neutral-900 border border-neutral-800 rounded-xl w-full overflow-hidden flex flex-col'
    : 'bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col';

  return (
    <div className={wrapperClass}>
      <div className={containerClass}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-800">
          <h2 className="text-lg font-semibold text-white">
            {post ? 'Edit Post' : 'Create New Post'}
          </h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="p-2 text-neutral-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-neutral-800 px-4">
          {(['content', 'seo', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? 'text-white border-b-2 border-blue-500'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4">
          {/* Content Tab */}
          {activeTab === 'content' && (
            <div className="space-y-6">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  placeholder="Enter post title..."
                  className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              {/* Slug */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Slug</label>
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 text-sm">/blog/</span>
                  <input
                    type="text"
                    value={formData.slug}
                    onChange={(e) => setFormData((prev) => ({ ...prev, slug: e.target.value }))}
                    placeholder="post-url-slug"
                    className="flex-1 px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Excerpt */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Excerpt</label>
                <textarea
                  value={formData.excerpt}
                  onChange={(e) => setFormData((prev) => ({ ...prev, excerpt: e.target.value }))}
                  placeholder="Short description for listings and previews..."
                  rows={3}
                  className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              {/* Content Editor */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Content</label>
                <RichTextEditor
                  content={formData.content}
                  contentJson={formData.content_json}
                  onChange={handleContentChange}
                  placeholder="Write your post content..."
                />
              </div>

              {/* Category & Author Row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Category
                  </label>
                  <select
                    value={formData.category_id || ''}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, category_id: e.target.value || undefined }))
                    }
                    className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select category...</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">Author</label>
                  <select
                    value={formData.author_id || ''}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, author_id: e.target.value || undefined }))
                    }
                    className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select author...</option>
                    {authors.map((author) => (
                      <option key={author.id} value={author.id}>
                        {author.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Tags */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">Tags</label>
                <div className="flex flex-wrap gap-2">
                  {tags.map((tag) => (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() => handleTagToggle(tag.id)}
                      className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                        formData.tag_ids?.includes(tag.id)
                          ? 'bg-blue-600 text-white'
                          : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
                      }`}
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Featured Image */}
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  <ImageIcon className="w-4 h-4 inline mr-1" />
                  Featured Image URL
                </label>
                <input
                  type="url"
                  value={formData.featured_image_url}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, featured_image_url: e.target.value }))
                  }
                  placeholder="https://example.com/image.jpg"
                  className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
                {formData.featured_image_url && (
                  <div className="mt-2">
                    <img
                      src={formData.featured_image_url}
                      alt="Featured preview"
                      className="max-h-40 rounded-lg object-cover"
                      onError={(e) => (e.currentTarget.style.display = 'none')}
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Featured Image Alt Text
                </label>
                <input
                  type="text"
                  value={formData.featured_image_alt}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, featured_image_alt: e.target.value }))
                  }
                  placeholder="Describe the image..."
                  className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          )}

          {/* SEO Tab */}
          {activeTab === 'seo' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Meta Title
                  <span className="text-neutral-500 ml-2 text-xs">
                    ({formData.meta_title?.length || 0}/70)
                  </span>
                </label>
                <input
                  type="text"
                  value={formData.meta_title}
                  onChange={(e) => setFormData((prev) => ({ ...prev, meta_title: e.target.value }))}
                  maxLength={70}
                  placeholder="SEO title (defaults to post title)"
                  className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Meta Description
                  <span className="text-neutral-500 ml-2 text-xs">
                    ({formData.meta_description?.length || 0}/160)
                  </span>
                </label>
                <textarea
                  value={formData.meta_description}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, meta_description: e.target.value }))
                  }
                  maxLength={160}
                  placeholder="Brief description for search engines..."
                  rows={3}
                  className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  <Link2 className="w-4 h-4 inline mr-1" />
                  Canonical URL
                </label>
                <input
                  type="url"
                  value={formData.canonical_url}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, canonical_url: e.target.value }))
                  }
                  placeholder="https://example.com/original-post"
                  className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-neutral-500 mt-1">Leave empty to use the default URL</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-2">
                  Open Graph Image URL
                </label>
                <input
                  type="url"
                  value={formData.og_image_url}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, og_image_url: e.target.value }))
                  }
                  placeholder="https://example.com/og-image.jpg"
                  className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-neutral-500 mt-1">
                  Image shown when shared on social media (defaults to featured image)
                </p>
              </div>

              {/* SEO Preview */}
              <div className="p-4 bg-neutral-800 rounded-lg">
                <h4 className="text-sm font-medium text-neutral-300 mb-3">Search Preview</h4>
                <div className="space-y-1">
                  <div className="text-blue-400 text-lg hover:underline cursor-pointer">
                    {formData.meta_title || formData.title || 'Post Title'}
                  </div>
                  <div className="text-green-500 text-sm">
                    stratum.ai/blog/{formData.slug || 'post-slug'}
                  </div>
                  <div className="text-neutral-400 text-sm">
                    {formData.meta_description || formData.excerpt || 'Post description...'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              {/* Status & Content Type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, status: e.target.value as PostStatus }))
                    }
                    className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    {statusOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-2">
                    Content Type
                  </label>
                  <select
                    value={formData.content_type}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        content_type: e.target.value as ContentType,
                      }))
                    }
                    className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  >
                    {contentTypeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Flags */}
              <div className="space-y-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_featured}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, is_featured: e.target.checked }))
                    }
                    className="w-5 h-5 rounded bg-neutral-800 border-neutral-700 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-neutral-300">Featured Post</span>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.allow_comments}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, allow_comments: e.target.checked }))
                    }
                    className="w-5 h-5 rounded bg-neutral-800 border-neutral-700 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-neutral-300">Allow Comments</span>
                </label>
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-neutral-800 bg-neutral-900/50">
          <div className="text-sm text-neutral-500">
            {post && (
              <>
                Last updated: {new Date(post.updated_at).toLocaleDateString()}
                {post.view_count > 0 && ` • ${post.view_count} views`}
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-neutral-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={isLoading || !formData.title}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              {isLoading ? 'Saving...' : 'Save Post'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PostEditor;
