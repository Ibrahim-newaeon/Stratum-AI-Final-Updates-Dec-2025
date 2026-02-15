/**
 * Stratum AI - Newsletter Campaign Editor
 *
 * Create / Edit page for newsletter campaigns.
 * Two-column layout: campaign details + rich text editor on the left,
 * audience filters + sender settings + actions on the right.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CalendarDaysIcon,
  EnvelopeIcon,
  PaperAirplaneIcon,
  UserGroupIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import RichTextEditor from '@/components/cms/RichTextEditor';
import {
  type AudienceFilters,
  type CampaignCreate,
  type CampaignUpdate,
  useAudienceCount,
  useCampaign,
  useCreateCampaign,
  useScheduleCampaign,
  useSendCampaign,
  useSendTestEmail,
  useTemplates,
  useUpdateCampaign,
} from '@/api/newsletter';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INPUT_CLASS =
  'bg-white/5 border border-white/[0.08] rounded-xl px-4 py-2.5 text-white placeholder:text-white/30 focus:border-[#00c7be] focus:outline-none focus:ring-1 focus:ring-[#00c7be]/50 w-full';

const BUTTON_PRIMARY =
  'bg-[#00c7be] hover:bg-[#00b5ad] text-black font-semibold rounded-xl px-4 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

const BUTTON_SECONDARY =
  'bg-white/5 border border-white/[0.08] hover:bg-white/10 text-white rounded-xl px-4 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

const CARD_CLASS = 'bg-white/5 border border-white/[0.08] rounded-2xl p-6';

const VARIABLE_TOKENS = [
  { label: 'First Name', token: '{{first_name}}' },
  { label: 'Full Name', token: '{{full_name}}' },
  { label: 'Company', token: '{{company_name}}' },
  { label: 'Email', token: '{{email}}' },
] as const;

const STATUS_OPTIONS = ['approved', 'pending', 'new'] as const;
const PLATFORM_OPTIONS = ['meta', 'google', 'tiktok', 'snapchat', 'organic'] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NewsletterCampaignEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const isEditMode = Boolean(id);
  const campaignId = id ? Number(id) : 0;

  // ---- Data fetching ----
  const { data: campaign, isLoading: campaignLoading } = useCampaign(campaignId);
  const { data: templates } = useTemplates();
  const createCampaign = useCreateCampaign();
  const updateCampaign = useUpdateCampaign();
  const sendCampaign = useSendCampaign();
  const scheduleCampaign = useScheduleCampaign();
  const sendTestEmail = useSendTestEmail();

  // ---- Form state ----
  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [preheaderText, setPreheaderText] = useState('');
  const [contentHtml, setContentHtml] = useState('');
  const [fromName, setFromName] = useState('');
  const [fromEmail, setFromEmail] = useState('');
  const [replyToEmail, setReplyToEmail] = useState('');
  const [audienceFilters, setAudienceFilters] = useState<AudienceFilters>({});
  const [templateId, setTemplateId] = useState<number | null>(null);

  // ---- Modal state ----
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showTestEmailModal, setShowTestEmailModal] = useState(false);
  const [scheduledAt, setScheduledAt] = useState('');
  const [testEmails, setTestEmails] = useState('');

  // ---- Content key for re-mounting editor when template loads ----
  const [editorKey, setEditorKey] = useState(0);

  // ---- Audience count ----
  const { data: audienceCount } = useAudienceCount(audienceFilters);

  // ---- Populate form when campaign data arrives (edit mode) ----
  useEffect(() => {
    if (campaign && isEditMode) {
      setName(campaign.name ?? '');
      setSubject(campaign.subject ?? '');
      setPreheaderText(campaign.preheader_text ?? '');
      setContentHtml(campaign.content_html ?? '');
      setFromName(campaign.from_name ?? '');
      setFromEmail(campaign.from_email ?? '');
      setReplyToEmail(campaign.reply_to_email ?? '');
      setAudienceFilters(campaign.audience_filters ?? {});
      setTemplateId(campaign.template_id ?? null);
      setEditorKey((k) => k + 1);
    }
  }, [campaign, isEditMode]);

  // ---- Helpers ----

  const buildPayload = (): CampaignCreate | CampaignUpdate => ({
    name,
    subject,
    preheader_text: preheaderText || undefined,
    content_html: contentHtml || undefined,
    template_id: templateId ?? undefined,
    from_name: fromName || undefined,
    from_email: fromEmail || undefined,
    reply_to_email: replyToEmail || undefined,
    audience_filters: Object.keys(audienceFilters).length > 0 ? audienceFilters : undefined,
  });

  const handleSaveDraft = async () => {
    try {
      if (isEditMode) {
        await updateCampaign.mutateAsync({ id: campaignId, data: buildPayload() as CampaignUpdate });
      } else {
        await createCampaign.mutateAsync(buildPayload() as CampaignCreate);
      }
      navigate('/dashboard/newsletter/campaigns');
    } catch {
      // mutation error handled by React Query
    }
  };

  const handleSendNow = async () => {
    if (!isEditMode) return;
    const confirmed = window.confirm(
      'Are you sure you want to send this campaign now? This action cannot be undone.',
    );
    if (!confirmed) return;
    try {
      await sendCampaign.mutateAsync(campaignId);
      navigate('/dashboard/newsletter/campaigns');
    } catch {
      // mutation error handled by React Query
    }
  };

  const handleSchedule = async () => {
    if (!isEditMode || !scheduledAt) return;
    try {
      await scheduleCampaign.mutateAsync({ id: campaignId, scheduled_at: scheduledAt });
      setShowScheduleModal(false);
      navigate('/dashboard/newsletter/campaigns');
    } catch {
      // mutation error handled by React Query
    }
  };

  const handleSendTest = async () => {
    if (!isEditMode || !testEmails.trim()) return;
    const emails = testEmails
      .split(',')
      .map((e) => e.trim())
      .filter(Boolean);
    try {
      await sendTestEmail.mutateAsync({ id: campaignId, emails });
      setShowTestEmailModal(false);
      setTestEmails('');
    } catch {
      // mutation error handled by React Query
    }
  };

  const handleTemplateSelect = (tplId: number | null) => {
    setTemplateId(tplId);
    if (tplId && templates) {
      const tpl = templates.find((t) => t.id === tplId);
      if (tpl) {
        setSubject(tpl.subject ?? '');
        setContentHtml(tpl.content_html ?? '');
        setEditorKey((k) => k + 1);
      }
    }
  };

  const insertVariable = (token: string) => {
    setContentHtml((prev) => prev + token);
    setEditorKey((k) => k + 1);
  };

  const toggleAudienceStatus = (status: string) => {
    setAudienceFilters((prev) => {
      const current = prev.status ?? [];
      const next = current.includes(status)
        ? current.filter((s) => s !== status)
        : [...current, status];
      return { ...prev, status: next.length > 0 ? next : undefined };
    });
  };

  const toggleAudiencePlatform = (platform: string) => {
    setAudienceFilters((prev) => {
      const current = prev.platforms ?? [];
      const next = current.includes(platform)
        ? current.filter((p) => p !== platform)
        : [...current, platform];
      return { ...prev, platforms: next.length > 0 ? next : undefined };
    });
  };

  // ---- Loading state ----
  if (isEditMode && campaignLoading) {
    return (
      <div className="flex items-center justify-center h-96 text-white/50">
        Loading campaign...
      </div>
    );
  }

  // ---- Render ----
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => navigate('/dashboard/newsletter/campaigns')}
          className="p-2 rounded-xl hover:bg-white/10 text-white/60 hover:text-white transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">
            {isEditMode ? 'Edit Campaign' : 'Create Campaign'}
          </h1>
          <p className="text-sm text-white/50 mt-0.5">
            {isEditMode
              ? 'Update your campaign details and content'
              : 'Set up a new email campaign'}
          </p>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ---------------------------------------------------------------- */}
        {/* Left Column - Campaign Details (2/3)                             */}
        {/* ---------------------------------------------------------------- */}
        <div className="lg:col-span-2 space-y-6">
          {/* Campaign Details Card */}
          <div className={CARD_CLASS}>
            <h2 className="text-lg font-semibold text-white mb-4">Campaign Details</h2>

            {/* Campaign Name */}
            <div className="space-y-1.5 mb-4">
              <label className="text-sm font-medium text-white/70">Campaign Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Spring Product Launch"
                className={INPUT_CLASS}
              />
            </div>

            {/* Subject Line */}
            <div className="space-y-1.5 mb-4">
              <label className="text-sm font-medium text-white/70">Subject Line</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. You won't want to miss this..."
                className={INPUT_CLASS}
              />
            </div>

            {/* Preheader Text */}
            <div className="space-y-1.5 mb-4">
              <label className="text-sm font-medium text-white/70">
                Preheader Text{' '}
                <span className="text-white/30 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={preheaderText}
                onChange={(e) => setPreheaderText(e.target.value)}
                placeholder="Preview text shown in inbox"
                className={INPUT_CLASS}
              />
              <p className="text-xs text-white/30">
                Appears after the subject line in most email clients. Keep it under 100 characters.
              </p>
            </div>

            {/* Template Selector */}
            <div className="space-y-1.5 mb-6">
              <label className="text-sm font-medium text-white/70">Load from Template</label>
              <select
                value={templateId ?? ''}
                onChange={(e) =>
                  handleTemplateSelect(e.target.value ? Number(e.target.value) : null)
                }
                className={INPUT_CLASS}
              >
                <option value="">-- Select a template --</option>
                {templates?.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name} ({tpl.category})
                  </option>
                ))}
              </select>
            </div>

            {/* Variable Insertion Buttons */}
            <div className="mb-4">
              <label className="text-sm font-medium text-white/70 block mb-2">
                Insert Variable
              </label>
              <div className="flex flex-wrap gap-2">
                {VARIABLE_TOKENS.map(({ label, token }) => (
                  <button
                    key={token}
                    type="button"
                    onClick={() => insertVariable(token)}
                    className="text-xs bg-white/5 border border-white/[0.08] hover:bg-white/10 text-white/70 hover:text-white rounded-lg px-3 py-1.5 transition-colors font-mono"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Rich Text Editor */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-white/70">Email Content</label>
              <RichTextEditor
                key={editorKey}
                content={contentHtml}
                onChange={(html: string) => setContentHtml(html)}
                placeholder="Write your email content..."
              />
            </div>
          </div>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Right Column - Sidebar (1/3)                                     */}
        {/* ---------------------------------------------------------------- */}
        <div className="space-y-6">
          {/* Audience Filters Panel */}
          <div className={CARD_CLASS}>
            <div className="flex items-center gap-2 mb-4">
              <UserGroupIcon className="w-5 h-5 text-[#00c7be]" />
              <h3 className="text-base font-semibold text-white">Audience</h3>
            </div>

            {/* Status Filter */}
            <div className="mb-4">
              <label className="text-sm font-medium text-white/70 block mb-2">Status</label>
              <div className="space-y-2">
                {STATUS_OPTIONS.map((status) => (
                  <label
                    key={status}
                    className="flex items-center gap-2 text-sm text-white/80 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={audienceFilters.status?.includes(status) ?? false}
                      onChange={() => toggleAudienceStatus(status)}
                      className="rounded border-white/20 bg-white/5 text-[#00c7be] focus:ring-[#00c7be]/50"
                    />
                    <span className="capitalize">{status}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Min Lead Score */}
            <div className="mb-4">
              <label className="text-sm font-medium text-white/70 block mb-1.5">
                Min Lead Score
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={audienceFilters.min_lead_score ?? ''}
                onChange={(e) =>
                  setAudienceFilters((prev) => ({
                    ...prev,
                    min_lead_score: e.target.value ? Number(e.target.value) : undefined,
                  }))
                }
                placeholder="0 - 100"
                className={INPUT_CLASS}
              />
            </div>

            {/* Platform Filter */}
            <div className="mb-4">
              <label className="text-sm font-medium text-white/70 block mb-2">Platform</label>
              <div className="space-y-2">
                {PLATFORM_OPTIONS.map((platform) => (
                  <label
                    key={platform}
                    className="flex items-center gap-2 text-sm text-white/80 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={audienceFilters.platforms?.includes(platform) ?? false}
                      onChange={() => toggleAudiencePlatform(platform)}
                      className="rounded border-white/20 bg-white/5 text-[#00c7be] focus:ring-[#00c7be]/50"
                    />
                    <span className="capitalize">{platform}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Live Audience Count */}
            <div className="pt-3 border-t border-white/[0.08]">
              <div className="flex items-center justify-between">
                <span className="text-sm text-white/50">Estimated audience</span>
                <span className="text-lg font-bold text-[#00c7be]">
                  {audienceCount !== undefined
                    ? audienceCount.toLocaleString()
                    : '--'}
                </span>
              </div>
            </div>
          </div>

          {/* Sender Settings Panel */}
          <div className={CARD_CLASS}>
            <div className="flex items-center gap-2 mb-4">
              <EnvelopeIcon className="w-5 h-5 text-[#00c7be]" />
              <h3 className="text-base font-semibold text-white">Sender Settings</h3>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">From Name</label>
                <input
                  type="text"
                  value={fromName}
                  onChange={(e) => setFromName(e.target.value)}
                  placeholder="Stratum AI"
                  className={INPUT_CLASS}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">From Email</label>
                <input
                  type="email"
                  value={fromEmail}
                  onChange={(e) => setFromEmail(e.target.value)}
                  placeholder="hello@stratum.ai"
                  className={INPUT_CLASS}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">Reply-To Email</label>
                <input
                  type="email"
                  value={replyToEmail}
                  onChange={(e) => setReplyToEmail(e.target.value)}
                  placeholder="support@stratum.ai"
                  className={INPUT_CLASS}
                />
              </div>
            </div>
          </div>

          {/* Actions Panel */}
          <div className={CARD_CLASS}>
            <h3 className="text-base font-semibold text-white mb-4">Actions</h3>

            <div className="space-y-3">
              {/* Save Draft */}
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={!name || !subject || createCampaign.isPending || updateCampaign.isPending}
                className={`${BUTTON_SECONDARY} w-full flex items-center justify-center gap-2`}
              >
                {createCampaign.isPending || updateCampaign.isPending
                  ? 'Saving...'
                  : 'Save Draft'}
              </button>

              {/* Send Test Email (only in edit mode) */}
              {isEditMode && (
                <button
                  type="button"
                  onClick={() => setShowTestEmailModal(true)}
                  className={`${BUTTON_SECONDARY} w-full flex items-center justify-center gap-2`}
                >
                  <EnvelopeIcon className="w-4 h-4" />
                  Send Test Email
                </button>
              )}

              {/* Schedule (only in edit mode) */}
              {isEditMode && (
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(true)}
                  className={`${BUTTON_SECONDARY} w-full flex items-center justify-center gap-2`}
                >
                  <CalendarDaysIcon className="w-4 h-4" />
                  Schedule
                </button>
              )}

              {/* Send Now (only in edit mode) */}
              {isEditMode && (
                <button
                  type="button"
                  onClick={handleSendNow}
                  disabled={sendCampaign.isPending}
                  className={`${BUTTON_PRIMARY} w-full flex items-center justify-center gap-2`}
                >
                  <PaperAirplaneIcon className="w-4 h-4" />
                  {sendCampaign.isPending ? 'Sending...' : 'Send Now'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Schedule Modal                                                      */}
      {/* ------------------------------------------------------------------ */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Schedule Campaign</h3>
              <button
                type="button"
                onClick={() => setShowScheduleModal(false)}
                className="p-1 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">Send Date &amp; Time</label>
                <input
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className={`${BUTTON_SECONDARY} flex-1`}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSchedule}
                  disabled={!scheduledAt || scheduleCampaign.isPending}
                  className={`${BUTTON_PRIMARY} flex-1`}
                >
                  {scheduleCampaign.isPending ? 'Scheduling...' : 'Confirm Schedule'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Test Email Modal                                                    */}
      {/* ------------------------------------------------------------------ */}
      {showTestEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#1a1a2e] border border-white/[0.08] rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Send Test Email</h3>
              <button
                type="button"
                onClick={() => setShowTestEmailModal(false)}
                className="p-1 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">
                  Recipient Emails
                </label>
                <textarea
                  value={testEmails}
                  onChange={(e) => setTestEmails(e.target.value)}
                  placeholder="email1@example.com, email2@example.com"
                  rows={3}
                  className={INPUT_CLASS}
                />
                <p className="text-xs text-white/30">
                  Separate multiple email addresses with commas.
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTestEmailModal(false)}
                  className={`${BUTTON_SECONDARY} flex-1`}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSendTest}
                  disabled={!testEmails.trim() || sendTestEmail.isPending}
                  className={`${BUTTON_PRIMARY} flex-1`}
                >
                  {sendTestEmail.isPending ? 'Sending...' : 'Send Test'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
