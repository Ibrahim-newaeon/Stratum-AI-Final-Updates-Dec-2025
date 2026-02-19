/**
 * CMS Pages Management
 * Manage static pages with template-based content editing,
 * JSON content editor, quick-create presets, and preview.
 */

import { useState } from 'react';
import {
  PlusIcon,
  RectangleStackIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
  GlobeAltIcon,
  EyeIcon,
  ChevronDownIcon,
  CodeBracketIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  CMSPage,
  PageCreate,
  PageUpdate,
  PageStatus,
  useAdminPages,
  useCreatePage,
  useUpdatePage,
  useDeletePage,
} from '@/api/cms';

// =============================================================================
// Constants
// =============================================================================

const PAGE_STATUS_STYLES: Record<PageStatus, { label: string; color: string; bg: string }> = {
  draft: { label: 'Draft', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  in_review: { label: 'In Review', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  approved: { label: 'Approved', color: 'text-green-400', bg: 'bg-green-500/20' },
  published: { label: 'Published', color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
  archived: { label: 'Archived', color: 'text-gray-500', bg: 'bg-gray-600/20' },
};

const TEMPLATES = [
  { value: 'default', label: 'Default (Prose)', description: 'HTML content — Privacy, Terms, etc.' },
  { value: 'full-width', label: 'Full Width', description: 'Full-width prose content' },
  { value: 'features', label: 'Features Grid', description: 'Feature cards with icons' },
  { value: 'pricing', label: 'Pricing Tiers', description: 'Pricing plans with feature lists' },
  { value: 'integrations', label: 'Integrations', description: 'Platform integration categories' },
  { value: 'about', label: 'About / Team', description: 'Team members, values, stats' },
  { value: 'careers', label: 'Careers / Jobs', description: 'Job listings and benefits' },
  { value: 'comparison', label: 'Comparison Table', description: 'Feature comparison vs competitors' },
  { value: 'changelog', label: 'Changelog Timeline', description: 'Release version history' },
  { value: 'case-studies', label: 'Case Studies', description: 'Customer success stories' },
  { value: 'resources', label: 'Resource Directory', description: 'Guides, webinars, whitepapers' },
  { value: 'status', label: 'Status Page', description: 'Service uptime and incidents' },
  { value: 'glossary', label: 'Glossary', description: 'Term definitions by category' },
  { value: 'api-docs', label: 'API Documentation', description: 'Endpoint reference docs' },
  { value: 'solution', label: 'Solution Marketing', description: 'CDP, Trust Engine, etc.' },
];

/** Quick-create presets for all known public pages */
const PAGE_PRESETS = [
  { slug: 'features', title: 'Features', template: 'features' },
  { slug: 'pricing', title: 'Pricing', template: 'pricing' },
  { slug: 'integrations', title: 'Integrations', template: 'integrations' },
  { slug: 'api-docs', title: 'API Reference', template: 'api-docs' },
  { slug: 'solutions-cdp', title: 'Customer Data Platform', template: 'solution' },
  { slug: 'solutions-audience-sync', title: 'Audience Sync', template: 'solution' },
  { slug: 'solutions-predictions', title: 'Predictive Analytics', template: 'solution' },
  { slug: 'solutions-trust-engine', title: 'Trust Engine', template: 'solution' },
  { slug: 'about', title: 'About Us', template: 'about' },
  { slug: 'careers', title: 'Careers', template: 'careers' },
  { slug: 'privacy', title: 'Privacy Policy', template: 'default' },
  { slug: 'terms', title: 'Terms of Service', template: 'default' },
  { slug: 'security', title: 'Security', template: 'default' },
  { slug: 'dpa', title: 'Data Processing Agreement', template: 'default' },
  { slug: 'docs', title: 'Documentation', template: 'default' },
  { slug: 'changelog', title: 'Changelog', template: 'changelog' },
  { slug: 'case-studies', title: 'Case Studies', template: 'case-studies' },
  { slug: 'resources', title: 'Resource Hub', template: 'resources' },
  { slug: 'status', title: 'System Status', template: 'status' },
  { slug: 'compare', title: 'Compare', template: 'comparison' },
  { slug: 'glossary', title: 'Glossary', template: 'glossary' },
];

/** JSON schema placeholders per template — shown when content_json is empty */
const JSON_PLACEHOLDERS: Record<string, string> = {
  features: JSON.stringify({ features: [{ iconName: 'ShieldCheckIcon', title: 'Feature Name', description: 'Feature description', color: '#8B5CF6' }] }, null, 2),
  pricing: JSON.stringify({ tiers: [{ name: 'Starter', price: '$499', period: '/mo', description: 'For growing teams', features: ['Feature 1', 'Feature 2'], cta: 'Start Free Trial', highlighted: false }] }, null, 2),
  about: JSON.stringify({ team: [{ name: 'Jane Doe', role: 'CEO', image: 'JD' }], values: [{ title: 'Trust First', description: 'Building reliable systems' }] }, null, 2),
  careers: JSON.stringify({ positions: [{ title: 'Sr. Engineer', department: 'Engineering', location: 'Remote', type: 'Full-time', salary: '$150k-$200k', description: 'Job description' }] }, null, 2),
  comparison: JSON.stringify({ competitors: [{ id: 'comp1', name: 'Competitor', tagline: 'Their tagline', color: '#666' }], features: [{ feature: 'Trust Gates', category: 'Core', stratum: 'Yes', competitors: { comp1: 'No' } }] }, null, 2),
  changelog: JSON.stringify({ releases: [{ version: 'v3.3.0', date: '2026-02-01', type: 'minor', highlights: ['New feature'], changes: [{ type: 'feature', text: 'Added X' }] }] }, null, 2),
  'case-studies': JSON.stringify({ studies: [{ company: 'Acme Corp', industry: 'E-commerce', logo: 'AC', challenge: 'The problem', solution: 'How we solved it', results: [{ metric: 'ROAS', value: '340%' }] }] }, null, 2),
  resources: JSON.stringify({ guides: [{ title: 'Getting Started', description: 'Quick start guide', iconName: 'BookOpenIcon', href: '/docs', tag: 'Guide' }], webinars: [], whitepapers: [] }, null, 2),
  status: JSON.stringify({ services: [{ name: 'API', status: 'operational', uptime: '99.99%', latency: '45ms' }], incidents: [] }, null, 2),
  glossary: JSON.stringify({ categories: [{ id: 'trust', name: 'Trust Engine', iconName: 'ShieldCheckIcon', color: '#8B5CF6', terms: [{ term: 'Signal Health', definition: 'Composite score of signal reliability' }] }] }, null, 2),
  'api-docs': JSON.stringify({ sections: [{ title: 'Getting Started', description: 'Quick start guide', iconName: 'RocketLaunchIcon', href: '#start' }], endpoints: [{ method: 'GET', path: '/api/v1/campaigns', description: 'List campaigns', category: 'Campaigns' }] }, null, 2),
  solution: JSON.stringify({ hero: { badge: 'Solution', title: 'Page Title', titleHighlight: 'Highlighted', description: 'Solution description', ctaText: 'Get Started', ctaLink: '/signup' }, features: [{ iconName: 'BoltIcon', title: 'Feature', description: 'Description' }] }, null, 2),
  integrations: JSON.stringify({ categories: [{ name: 'Ad Platforms', description: 'Connect your ad accounts', platforms: [{ name: 'Meta', description: 'Facebook & Instagram', iconName: 'meta', color: '#1877F2' }] }] }, null, 2),
};

/** Templates that use content_json instead of plain HTML content */
const STRUCTURED_TEMPLATES = ['features', 'pricing', 'integrations', 'about', 'careers', 'comparison', 'changelog', 'case-studies', 'resources', 'status', 'glossary', 'api-docs', 'solution'];

// =============================================================================
// Component
// =============================================================================

export default function CMSPages() {
  const { data, isLoading } = useAdminPages();
  const createMutation = useCreatePage();
  const updateMutation = useUpdatePage();
  const deleteMutation = useDeletePage();

  const [showEditor, setShowEditor] = useState(false);
  const [editingPage, setEditingPage] = useState<CMSPage | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [showPresets, setShowPresets] = useState(false);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [contentJsonStr, setContentJsonStr] = useState('');
  const [formData, setFormData] = useState<PageCreate>({
    title: '',
    slug: '',
    content: '',
    status: 'draft',
    template: 'default',
    show_in_navigation: false,
    navigation_order: 0,
  });

  const pages = data?.pages || [];
  const existingSlugs = new Set(pages.map((p) => p.slug));
  const isStructured = STRUCTURED_TEMPLATES.includes(formData.template || '');

  const openEditor = (page?: CMSPage) => {
    setJsonError(null);
    if (page) {
      setEditingPage(page);
      const jsonStr = page.content_json ? JSON.stringify(page.content_json, null, 2) : '';
      setContentJsonStr(jsonStr);
      setFormData({
        title: page.title,
        slug: page.slug,
        content: page.content || '',
        status: page.status,
        meta_title: page.meta_title || '',
        meta_description: page.meta_description || '',
        template: page.template,
        show_in_navigation: page.show_in_navigation,
        navigation_label: page.navigation_label || '',
        navigation_order: page.navigation_order,
      });
    } else {
      setEditingPage(null);
      setContentJsonStr('');
      setFormData({
        title: '',
        slug: '',
        content: '',
        status: 'draft',
        template: 'default',
        show_in_navigation: false,
        navigation_order: 0,
      });
    }
    setShowEditor(true);
  };

  const openPreset = (preset: (typeof PAGE_PRESETS)[number]) => {
    setJsonError(null);
    setEditingPage(null);
    setContentJsonStr('');
    setFormData({
      title: preset.title,
      slug: preset.slug,
      content: '',
      status: 'draft',
      template: preset.template,
      show_in_navigation: false,
      navigation_order: 0,
    });
    setShowPresets(false);
    setShowEditor(true);
  };

  const handleSave = () => {
    let saveData = { ...formData };

    // Parse content_json if structured template
    if (isStructured && contentJsonStr.trim()) {
      try {
        const parsed = JSON.parse(contentJsonStr);
        saveData = { ...saveData, content_json: parsed };
        setJsonError(null);
      } catch (e) {
        setJsonError(`Invalid JSON: ${e instanceof Error ? e.message : 'Parse error'}`);
        return;
      }
    } else if (isStructured) {
      // Clear content_json if empty
      saveData = { ...saveData, content_json: undefined };
    }

    if (editingPage) {
      updateMutation.mutate(
        { id: editingPage.id, data: saveData as PageUpdate },
        { onSuccess: () => setShowEditor(false) }
      );
    } else {
      createMutation.mutate(saveData, {
        onSuccess: () => setShowEditor(false),
      });
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => setDeleteConfirm(null),
    });
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(contentJsonStr);
      setContentJsonStr(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch (e) {
      setJsonError(`Invalid JSON: ${e instanceof Error ? e.message : 'Parse error'}`);
    }
  };

  const generateSlug = (title: string) => {
    return title
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[-\s]+/g, '-');
  };

  const handlePreview = (slug: string) => {
    // Map slug to URL path
    const url = slug.startsWith('solutions-')
      ? `/${slug.replace('solutions-', 'solutions/')}`
      : `/${slug}`;
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Pages</h1>
          <p className="text-white/60 mt-1">
            Manage static website pages &middot; {pages.length} total
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Quick Create Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowPresets(!showPresets)}
              className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 hover:bg-white/10 text-white rounded-lg font-medium transition-colors"
            >
              Quick Create
              <ChevronDownIcon className="w-4 h-4" />
            </button>
            {showPresets && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setShowPresets(false)} />
                <div className="absolute right-0 top-full mt-2 z-40 w-72 bg-neutral-900 border border-white/10 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                  <div className="p-2">
                    <p className="text-xs font-medium text-white/40 px-3 py-2 uppercase tracking-wider">
                      Page Presets
                    </p>
                    {PAGE_PRESETS.map((preset) => {
                      const exists = existingSlugs.has(preset.slug);
                      return (
                        <button
                          key={preset.slug}
                          onClick={() => !exists && openPreset(preset)}
                          disabled={exists}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                            exists
                              ? 'opacity-40 cursor-not-allowed'
                              : 'hover:bg-white/5 text-white'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{preset.title}</span>
                            {exists && (
                              <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
                            )}
                          </div>
                          <span className="text-white/40 text-xs">/{preset.slug}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </div>

          <button
            onClick={() => openEditor()}
            className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
          >
            <PlusIcon className="w-5 h-5" />
            New Page
          </button>
        </div>
      </div>

      {/* Pages List */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
          </div>
        ) : pages.length === 0 ? (
          <div className="text-center py-20">
            <RectangleStackIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 mb-2">No pages yet</p>
            <p className="text-white/40 text-sm mb-6">
              Use Quick Create to set up all public pages instantly
            </p>
            <button
              onClick={() => openEditor()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Create your first page
            </button>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {pages.map((page) => {
              const statusStyle = PAGE_STATUS_STYLES[page.status];
              const templateInfo = TEMPLATES.find((t) => t.value === page.template);
              return (
                <div
                  key={page.id}
                  className="flex items-center justify-between px-6 py-4 hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                      <RectangleStackIcon className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-medium truncate">{page.title}</p>
                      <div className="flex items-center gap-2 text-xs text-white/40">
                        <span>/{page.slug}</span>
                        <span>&middot;</span>
                        <span>{templateInfo?.label || page.template}</span>
                        {page.show_in_navigation && (
                          <>
                            <span>&middot;</span>
                            <GlobeAltIcon className="w-3 h-3 inline" />
                            <span>In Nav</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.color}`}
                    >
                      {statusStyle.label}
                    </span>
                    <button
                      onClick={() => handlePreview(page.slug)}
                      className="p-1.5 text-white/40 hover:text-cyan-400 transition-colors"
                      title="Preview page"
                    >
                      <EyeIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => openEditor(page)}
                      className="p-1.5 text-white/40 hover:text-white transition-colors"
                      title="Edit page"
                    >
                      <PencilSquareIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(page.id)}
                      className="p-1.5 text-white/40 hover:text-red-400 transition-colors"
                      title="Delete page"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Page Editor Modal */}
      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">
                {editingPage ? 'Edit Page' : 'Create New Page'}
              </h2>
              <div className="flex items-center gap-2">
                {editingPage && (
                  <button
                    onClick={() => handlePreview(formData.slug || editingPage.slug)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-cyan-400 hover:bg-cyan-500/10 rounded-lg transition-colors"
                  >
                    <EyeIcon className="w-4 h-4" />
                    Preview
                  </button>
                )}
                <button
                  onClick={() => setShowEditor(false)}
                  className="p-2 text-white/40 hover:text-white"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-5">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => {
                    const title = e.target.value;
                    setFormData((f) => ({
                      ...f,
                      title,
                      slug: f.slug || generateSlug(title),
                    }));
                  }}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="Page title"
                />
              </div>

              {/* Slug */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Slug</label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => setFormData((f) => ({ ...f, slug: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="page-url-slug"
                />
              </div>

              {/* Status + Template */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, status: e.target.value as PageStatus }))
                    }
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {Object.entries(PAGE_STATUS_STYLES).map(([val, { label }]) => (
                      <option key={val} value={val} className="bg-neutral-900">
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Template</label>
                  <select
                    value={formData.template}
                    onChange={(e) => setFormData((f) => ({ ...f, template: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {TEMPLATES.map((t) => (
                      <option key={t.value} value={t.value} className="bg-neutral-900">
                        {t.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-white/30 mt-1">
                    {TEMPLATES.find((t) => t.value === formData.template)?.description}
                  </p>
                </div>
              </div>

              {/* Content (HTML) — shown for prose templates */}
              {!isStructured && (
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    Content (HTML)
                  </label>
                  <textarea
                    value={formData.content}
                    onChange={(e) => setFormData((f) => ({ ...f, content: e.target.value }))}
                    rows={10}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none font-mono text-sm"
                    placeholder="HTML content for the page..."
                  />
                </div>
              )}

              {/* Content JSON — shown for structured templates */}
              {isStructured && (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="flex items-center gap-2 text-sm font-medium text-white/70">
                      <CodeBracketIcon className="w-4 h-4" />
                      Content JSON
                    </label>
                    <button
                      onClick={formatJson}
                      className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
                    >
                      Format JSON
                    </button>
                  </div>
                  <textarea
                    value={contentJsonStr}
                    onChange={(e) => {
                      setContentJsonStr(e.target.value);
                      setJsonError(null);
                    }}
                    rows={14}
                    className={`w-full px-4 py-3 bg-white/5 border rounded-lg text-white placeholder-white/20 focus:outline-none resize-none font-mono text-sm leading-relaxed ${
                      jsonError
                        ? 'border-red-500/50 focus:border-red-500'
                        : 'border-white/10 focus:border-purple-500/50'
                    }`}
                    placeholder={JSON_PLACEHOLDERS[formData.template || ''] || '{\n  \n}'}
                    spellCheck={false}
                  />
                  {jsonError && (
                    <div className="flex items-center gap-2 mt-2 text-red-400 text-xs">
                      <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0" />
                      {jsonError}
                    </div>
                  )}
                </div>
              )}

              {/* SEO Fields */}
              <div className="border-t border-white/5 pt-5">
                <p className="text-xs font-medium text-white/40 uppercase tracking-wider mb-4">
                  SEO Metadata
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">
                      Meta Title
                    </label>
                    <input
                      type="text"
                      value={formData.meta_title || ''}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, meta_title: e.target.value }))
                      }
                      maxLength={70}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                      placeholder="SEO title (max 70 chars)"
                    />
                    <p className="text-xs text-white/30 mt-1 text-right">
                      {(formData.meta_title || '').length}/70
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white/70 mb-1.5">
                      Meta Description
                    </label>
                    <textarea
                      value={formData.meta_description || ''}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, meta_description: e.target.value }))
                      }
                      rows={2}
                      maxLength={160}
                      className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                      placeholder="SEO description (max 160 chars)"
                    />
                    <p className="text-xs text-white/30 mt-1 text-right">
                      {(formData.meta_description || '').length}/160
                    </p>
                  </div>
                </div>
              </div>

              {/* Navigation Settings */}
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.show_in_navigation}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, show_in_navigation: e.target.checked }))
                    }
                    className="w-4 h-4 rounded bg-white/5 border-white/20 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-sm text-white/70">Show in navigation</span>
                </label>
                {formData.show_in_navigation && (
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-white/70">Label:</label>
                    <input
                      type="text"
                      value={formData.navigation_label || ''}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, navigation_label: e.target.value }))
                      }
                      className="w-28 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-purple-500/50"
                      placeholder="Nav label"
                    />
                    <label className="text-sm text-white/70">Order:</label>
                    <input
                      type="number"
                      value={formData.navigation_order || 0}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, navigation_order: Number(e.target.value) }))
                      }
                      className="w-20 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-purple-500/50"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 p-4 border-t border-white/10">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 text-white/60 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={
                  !formData.title || createMutation.isPending || updateMutation.isPending
                }
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingPage
                    ? 'Update Page'
                    : 'Create Page'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Page</h3>
            <p className="text-white/60 mb-6">
              Are you sure? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-white/60 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
