/**
 * Add Competitor Modal - Shared Component
 * Used by both Benchmarks and Competitors pages
 */

import { useState } from 'react';
import { useCreateCompetitor, useCompetitors } from '@/api/hooks';
import {
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  CheckIcon,
  PlusIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

// Countries for Meta Ads Library and Google Transparency
const COUNTRIES = [
  { code: 'SA', name: 'Saudi Arabia', flag: '🇸🇦' },
  { code: 'AE', name: 'United Arab Emirates', flag: '🇦🇪' },
  { code: 'EG', name: 'Egypt', flag: '🇪🇬' },
  { code: 'KW', name: 'Kuwait', flag: '🇰🇼' },
  { code: 'QA', name: 'Qatar', flag: '🇶🇦' },
  { code: 'BH', name: 'Bahrain', flag: '🇧🇭' },
  { code: 'OM', name: 'Oman', flag: '🇴🇲' },
  { code: 'JO', name: 'Jordan', flag: '🇯🇴' },
  { code: 'LB', name: 'Lebanon', flag: '🇱🇧' },
  { code: 'US', name: 'United States', flag: '🇺🇸' },
  { code: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
  { code: 'DE', name: 'Germany', flag: '🇩🇪' },
  { code: 'FR', name: 'France', flag: '🇫🇷' },
  { code: 'IN', name: 'India', flag: '🇮🇳' },
  { code: 'PK', name: 'Pakistan', flag: '🇵🇰' },
  { code: 'TR', name: 'Turkey', flag: '🇹🇷' },
];

const PLATFORMS = [
  { id: 'meta', name: 'Meta (Facebook/Instagram)', icon: 'M' },
  { id: 'google', name: 'Google Ads', icon: 'G' },
  { id: 'tiktok', name: 'TikTok', icon: 'T' },
  { id: 'snapchat', name: 'Snapchat', icon: 'S' },
];

interface AddCompetitorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddCompetitorModal({ isOpen, onClose, onSuccess }: AddCompetitorModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newCompetitor, setNewCompetitor] = useState({
    name: '',
    domain: '',
    country: 'SA',
    platforms: ['meta', 'google'] as string[],
  });

  const createCompetitor = useCreateCompetitor();
  const { refetch: refetchCompetitors } = useCompetitors();

  // Generate Meta Ads Library URL
  const getMetaAdsLibraryUrl = (name: string, country: string) => {
    return `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=${country}&q=${encodeURIComponent(name)}&search_type=keyword_unordered`;
  };

  // Generate Google Ads Transparency URL
  const getGoogleTransparencyUrl = (name: string) => {
    return `https://adstransparency.google.com/?query=${encodeURIComponent(name)}`;
  };

  // Toggle platform selection
  const togglePlatform = (platformId: string) => {
    setNewCompetitor((prev) => ({
      ...prev,
      platforms: prev.platforms.includes(platformId)
        ? prev.platforms.filter((p) => p !== platformId)
        : [...prev.platforms, platformId],
    }));
  };

  // Handle form submission
  const handleAddCompetitor = async () => {
    if (!newCompetitor.name || !newCompetitor.domain) return;

    setIsSubmitting(true);
    try {
      await createCompetitor.mutateAsync({
        name: newCompetitor.name,
        domain: newCompetitor.domain,
        country: newCompetitor.country,
        platforms: newCompetitor.platforms,
      });
      setNewCompetitor({ name: '', domain: '', country: 'SA', platforms: ['meta', 'google'] });
      refetchCompetitors();
      onSuccess?.();
      onClose();
    } catch (error) {
      // Error handled by mutation
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle close and reset form
  const handleClose = () => {
    setNewCompetitor({ name: '', domain: '', country: 'SA', platforms: ['meta', 'google'] });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-card rounded-2xl shadow-2xl border overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold">Add Competitor</h2>
            <p className="text-sm text-muted-foreground">
              Track competitor ads via Meta Ads Library & Google Transparency
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-5">
          {/* Competitor Name */}
          <div>
            <label className="block text-sm font-medium mb-2">Competitor Name *</label>
            <input
              type="text"
              value={newCompetitor.name}
              onChange={(e) => setNewCompetitor((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g., Competitor Inc"
              className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Domain/Website */}
          <div>
            <label className="block text-sm font-medium mb-2">Website / Domain *</label>
            <input
              type="text"
              value={newCompetitor.domain}
              onChange={(e) =>
                setNewCompetitor((prev) => ({ ...prev, domain: e.target.value }))
              }
              placeholder="e.g., competitor.com"
              className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Used to search ads in Meta Ads Library and Google Transparency
            </p>
          </div>

          {/* Country Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Competitor's Country *</label>
            <select
              value={newCompetitor.country}
              onChange={(e) =>
                setNewCompetitor((prev) => ({ ...prev, country: e.target.value }))
              }
              className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {COUNTRIES.map((country) => (
                <option key={country.code} value={country.code}>
                  {country.flag} {country.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              Select the country where competitor runs ads (for Meta Ads Library filter)
            </p>
          </div>

          {/* Platform Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Platforms to Track</label>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map((platform) => (
                <button
                  key={platform.id}
                  type="button"
                  onClick={() => togglePlatform(platform.id)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all',
                    newCompetitor.platforms.includes(platform.id)
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:border-primary/50'
                  )}
                >
                  <span className="w-5 h-5 rounded bg-muted flex items-center justify-center text-xs font-bold">
                    {platform.icon}
                  </span>
                  <span className="text-sm">{platform.name}</span>
                  {newCompetitor.platforms.includes(platform.id) && (
                    <CheckIcon className="w-4 h-4" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Links Preview */}
          {newCompetitor.name && (
            <div className="p-4 rounded-lg bg-muted/50 space-y-3">
              <p className="text-sm font-medium">
                Preview Ad Library Links for "{newCompetitor.name}":
              </p>
              <div className="space-y-2">
                <a
                  href={getMetaAdsLibraryUrl(newCompetitor.name, newCompetitor.country)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:underline"
                >
                  <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                  Search "{newCompetitor.name}" in Meta Ads Library (
                  {COUNTRIES.find((c) => c.code === newCompetitor.country)?.name})
                </a>
                <a
                  href={getGoogleTransparencyUrl(newCompetitor.name)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:underline"
                >
                  <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                  Search "{newCompetitor.name}" in Google Ads Transparency
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-muted/30">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleAddCompetitor}
            disabled={!newCompetitor.name || !newCompetitor.domain || isSubmitting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
                Adding...
              </>
            ) : (
              <>
                <PlusIcon className="w-4 h-4" />
                Add Competitor
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddCompetitorModal;
