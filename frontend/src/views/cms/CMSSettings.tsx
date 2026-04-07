/**
 * CMS Settings
 * General CMS configuration and preferences
 */

import { useState } from 'react';
import {
  GlobeAltIcon,
  PaintBrushIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

interface CMSSettingsData {
  siteName: string;
  siteDescription: string;
  postsPerPage: number;
  defaultPostStatus: string;
  allowComments: boolean;
  moderateComments: boolean;
  enableRSS: boolean;
  dateFormat: string;
  timezone: string;
}

export default function CMSSettings() {
  const [settings, setSettings] = useState<CMSSettingsData>({
    siteName: 'Stratum AI Blog',
    siteDescription: 'Revenue Operating System insights, guides, and updates',
    postsPerPage: 12,
    defaultPostStatus: 'draft',
    allowComments: true,
    moderateComments: true,
    enableRSS: true,
    dateFormat: 'MMM DD, YYYY',
    timezone: 'UTC',
  });
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // Settings would be persisted to the backend
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">CMS Settings</h1>
        <p className="text-white/60 mt-1">Configure your content management preferences</p>
      </div>

      {/* General Settings */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10">
          <GlobeAltIcon className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-semibold text-white">General</h2>
        </div>
        <div className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">Site Name</label>
            <input
              type="text"
              value={settings.siteName}
              onChange={(e) => setSettings((s) => ({ ...s, siteName: e.target.value }))}
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1.5">
              Site Description
            </label>
            <textarea
              value={settings.siteDescription}
              onChange={(e) => setSettings((s) => ({ ...s, siteDescription: e.target.value }))}
              rows={2}
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
            />
          </div>
        </div>
      </div>

      {/* Content Settings */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10">
          <PaintBrushIcon className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-white">Content</h2>
        </div>
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">
                Posts Per Page
              </label>
              <input
                type="number"
                value={settings.postsPerPage}
                onChange={(e) =>
                  setSettings((s) => ({ ...s, postsPerPage: Number(e.target.value) }))
                }
                min={1}
                max={50}
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">
                Default Post Status
              </label>
              <select
                value={settings.defaultPostStatus}
                onChange={(e) =>
                  setSettings((s) => ({ ...s, defaultPostStatus: e.target.value }))
                }
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
              >
                <option value="draft" className="bg-neutral-900">Draft</option>
                <option value="in_review" className="bg-neutral-900">In Review</option>
                <option value="published" className="bg-neutral-900">Published</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">
                Date Format
              </label>
              <select
                value={settings.dateFormat}
                onChange={(e) => setSettings((s) => ({ ...s, dateFormat: e.target.value }))}
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
              >
                <option value="MMM DD, YYYY" className="bg-neutral-900">Jan 15, 2026</option>
                <option value="DD/MM/YYYY" className="bg-neutral-900">15/01/2026</option>
                <option value="YYYY-MM-DD" className="bg-neutral-900">2026-01-15</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-white/70 mb-1.5">Timezone</label>
              <select
                value={settings.timezone}
                onChange={(e) => setSettings((s) => ({ ...s, timezone: e.target.value }))}
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
              >
                <option value="UTC" className="bg-neutral-900">UTC</option>
                <option value="America/New_York" className="bg-neutral-900">Eastern (US)</option>
                <option value="America/Chicago" className="bg-neutral-900">Central (US)</option>
                <option value="America/Denver" className="bg-neutral-900">Mountain (US)</option>
                <option value="America/Los_Angeles" className="bg-neutral-900">Pacific (US)</option>
                <option value="Europe/London" className="bg-neutral-900">London</option>
                <option value="Asia/Dubai" className="bg-neutral-900">Dubai</option>
                <option value="Asia/Riyadh" className="bg-neutral-900">Riyadh</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Comments & Interaction */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10">
          <ShieldCheckIcon className="w-5 h-5 text-green-400" />
          <h2 className="text-lg font-semibold text-white">Comments & Interaction</h2>
        </div>
        <div className="p-6 space-y-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <span className="text-white font-medium">Allow Comments</span>
              <p className="text-sm text-white/50">Enable comments on new posts by default</p>
            </div>
            <div
              className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${settings.allowComments ? 'bg-purple-600' : 'bg-white/10'}`}
              onClick={() =>
                setSettings((s) => ({ ...s, allowComments: !s.allowComments }))
              }
            >
              <div
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${settings.allowComments ? 'translate-x-7' : 'translate-x-1'}`}
              />
            </div>
          </label>

          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <span className="text-white font-medium">Moderate Comments</span>
              <p className="text-sm text-white/50">Require approval before comments appear</p>
            </div>
            <div
              className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${settings.moderateComments ? 'bg-purple-600' : 'bg-white/10'}`}
              onClick={() =>
                setSettings((s) => ({ ...s, moderateComments: !s.moderateComments }))
              }
            >
              <div
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${settings.moderateComments ? 'translate-x-7' : 'translate-x-1'}`}
              />
            </div>
          </label>

          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <span className="text-white font-medium">RSS Feed</span>
              <p className="text-sm text-white/50">Generate RSS feed for published posts</p>
            </div>
            <div
              className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${settings.enableRSS ? 'bg-purple-600' : 'bg-white/10'}`}
              onClick={() =>
                setSettings((s) => ({ ...s, enableRSS: !s.enableRSS }))
              }
            >
              <div
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${settings.enableRSS ? 'translate-x-7' : 'translate-x-1'}`}
              />
            </div>
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-4">
        {saved && (
          <span className="text-sm text-green-400">Settings saved successfully</span>
        )}
        <button
          onClick={handleSave}
          className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}
