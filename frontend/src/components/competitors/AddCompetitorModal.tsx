/**
 * Add Competitor Modal - Shared Component
 * Used by both Benchmarks and Competitors pages
 *
 * Features:
 * - Enter competitor name + domain + country
 * - "Scan" button scrapes website for FB/IG links + searches Meta Ad Library
 * - Shows scraped social links and ad presence results
 * - "Add & Track" saves competitor to DB
 */

import { useState } from 'react';
import { useCreateCompetitor, useCompetitors, useScanCompetitor } from '@/api/hooks';
import type { CompetitorScanResult } from '@/api/competitors';
import {
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  CheckCircleIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  XCircleIcon,
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
    fb_page_name: '',
  });

  // Scan state
  const [scanResult, setScanResult] = useState<CompetitorScanResult | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  const createCompetitor = useCreateCompetitor();
  const scanCompetitor = useScanCompetitor();
  const { refetch: refetchCompetitors } = useCompetitors();

  // Generate Meta Ads Library URL
  const getMetaAdsLibraryUrl = (name: string, country: string, fbPageName?: string) => {
    const query = fbPageName || name;
    return `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=${country}&q=${encodeURIComponent(query)}&search_type=keyword_unordered`;
  };

  // Generate Google Ads Transparency URL - search by full website URL with country filter
  const getGoogleTransparencyUrl = (domain: string, country: string = 'SA') => {
    // Build full URL (Google Transparency needs https://www. prefix for best results)
    let fullUrl = domain.replace(/\/+$/, '');
    if (!fullUrl.startsWith('http')) {
      fullUrl = `https://www.${fullUrl}`;
    }
    return `https://adstransparency.google.com/?query=${encodeURIComponent(fullUrl)}&region=${country}`;
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

  // Handle scan
  const handleScan = async () => {
    if (!newCompetitor.name || !newCompetitor.domain) return;

    setIsScanning(true);
    setScanError(null);
    setScanResult(null);

    try {
      const result = await scanCompetitor.mutateAsync({
        domain: newCompetitor.domain,
        name: newCompetitor.name,
        country: newCompetitor.country,
        fb_page_name: newCompetitor.fb_page_name || undefined,
      });
      setScanResult(result);
    } catch (err) {
      setScanError(err instanceof Error ? err.message : 'Scan failed. Try again.');
    } finally {
      setIsScanning(false);
    }
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
      resetForm();
      refetchCompetitors();
      onSuccess?.();
      onClose();
    } catch (error) {
      // Error handled by mutation
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setNewCompetitor({ name: '', domain: '', country: 'SA', platforms: ['meta', 'google'], fb_page_name: '' });
    setScanResult(null);
    setScanError(null);
  };

  // Handle close and reset form
  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  const socialLinks = scanResult?.social_links;
  const adLibrary = scanResult?.ad_library;
  const hasSocialLinks = socialLinks && Object.values(socialLinks).some(Boolean);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-card rounded-2xl shadow-2xl border overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b shrink-0">
          <div>
            <h2 className="text-xl font-semibold">Add Competitor</h2>
            <p className="text-sm text-muted-foreground">
              Scan website for social links & check Meta Ad Library
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto flex-1">
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
                We'll scrape this website to find their Facebook & Instagram accounts
              </p>
            </div>

            {/* Facebook Page Name */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Facebook Page Name
              </label>
              <input
                type="text"
                value={newCompetitor.fb_page_name}
                onChange={(e) => setNewCompetitor((prev) => ({ ...prev, fb_page_name: e.target.value }))}
                placeholder="e.g. Nike"
                className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Used to search Meta Ads Library directly — no scraping needed
              </p>
            </div>

            {/* Country Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Country *</label>
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
                Used to search Meta Ad Library for ads in this country
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

            {/* Scan Button */}
            {newCompetitor.name && newCompetitor.domain && (
              <button
                onClick={handleScan}
                disabled={isScanning}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {isScanning ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Scanning website & Meta Ad Library...
                  </>
                ) : (
                  <>
                    <MagnifyingGlassIcon className="w-5 h-5" />
                    Scan Competitor
                  </>
                )}
              </button>
            )}

            {/* Scan Error */}
            {scanError && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">
                <div className="flex items-center gap-2">
                  <ExclamationTriangleIcon className="w-5 h-5 shrink-0" />
                  {scanError}
                </div>
              </div>
            )}

            {/* Scan Results */}
            {scanResult && (
              <div className="space-y-4">
                {/* Social Links Found */}
                <div className="p-4 rounded-lg bg-muted/50 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {hasSocialLinks ? (
                      <CheckCircleIcon className="w-5 h-5 text-green-500" />
                    ) : (
                      <XCircleIcon className="w-5 h-5 text-amber-500" />
                    )}
                    Social Media Links
                  </div>

                  {hasSocialLinks ? (
                    <div className="space-y-2">
                      {socialLinks.facebook && (
                        <a
                          href={socialLinks.facebook}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-sm text-blue-500 hover:underline"
                        >
                          <span className="w-6 h-6 rounded bg-blue-500/10 flex items-center justify-center text-xs font-bold text-blue-500">
                            f
                          </span>
                          {socialLinks.facebook}
                          <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                        </a>
                      )}
                      {socialLinks.instagram && (
                        <a
                          href={socialLinks.instagram}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-sm text-pink-500 hover:underline"
                        >
                          <span className="w-6 h-6 rounded bg-pink-500/10 flex items-center justify-center text-xs font-bold text-pink-500">
                            IG
                          </span>
                          {socialLinks.instagram}
                          <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                        </a>
                      )}
                      {socialLinks.twitter && (
                        <a
                          href={socialLinks.twitter}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-sm text-sky-500 hover:underline"
                        >
                          <span className="w-6 h-6 rounded bg-sky-500/10 flex items-center justify-center text-xs font-bold text-sky-500">
                            X
                          </span>
                          {socialLinks.twitter}
                          <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                        </a>
                      )}
                      {socialLinks.tiktok && (
                        <a
                          href={socialLinks.tiktok}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-sm text-foreground hover:underline"
                        >
                          <span className="w-6 h-6 rounded bg-muted flex items-center justify-center text-xs font-bold">
                            TT
                          </span>
                          {socialLinks.tiktok}
                          <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                        </a>
                      )}
                      {socialLinks.linkedin && (
                        <a
                          href={socialLinks.linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
                        >
                          <span className="w-6 h-6 rounded bg-blue-600/10 flex items-center justify-center text-xs font-bold text-blue-600">
                            in
                          </span>
                          {socialLinks.linkedin}
                          <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      No social media links found on this website
                      {scanResult.scrape_error && ` (${scanResult.scrape_error})`}
                    </p>
                  )}
                </div>

                {/* Meta Ad Library Results */}
                <div
                  className={cn(
                    'p-4 rounded-lg border space-y-3',
                    adLibrary?.has_ads
                      ? 'bg-green-500/5 border-green-500/20'
                      : 'bg-amber-500/5 border-amber-500/20'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      {adLibrary?.has_ads ? (
                        <>
                          <CheckCircleIcon className="w-5 h-5 text-green-500" />
                          <span className="text-green-500">Active Ads Found</span>
                        </>
                      ) : (
                        <>
                          <XCircleIcon className="w-5 h-5 text-amber-500" />
                          <span className="text-amber-500">No Active Ads</span>
                        </>
                      )}
                    </div>
                    {adLibrary?.has_ads && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/10 text-green-500 font-medium">
                        {adLibrary.ad_count}+ ads
                      </span>
                    )}
                  </div>

                  {/* Show which account was searched */}
                  <div className="text-xs text-muted-foreground space-y-0.5">
                    {scanResult.fb_page_name && (
                      <p>FB Page: <span className="font-medium text-foreground">{scanResult.fb_page_name}</span></p>
                    )}
                    {scanResult.ig_account_name && (
                      <p>IG Account: <span className="font-medium text-foreground">@{scanResult.ig_account_name}</span></p>
                    )}
                    {adLibrary?.search_query && (
                      <p>Searched: <span className="font-medium text-foreground">"{adLibrary.search_query}"</span></p>
                    )}
                    {adLibrary?.has_ads && adLibrary.page_name && (
                      <p>Ad Page: <span className="font-medium text-foreground">{adLibrary.page_name}</span></p>
                    )}
                  </div>

                  {/* Show first few ads */}
                  {adLibrary?.ads && adLibrary.ads.length > 0 && (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {adLibrary.ads.slice(0, 5).map((ad, i) => (
                        <div
                          key={ad.id || i}
                          className="p-3 rounded-lg bg-background/50 border text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium truncate flex-1">
                              {ad.link_title || ad.page_name || 'Ad'}
                            </span>
                            {ad.snapshot_url && (
                              <a
                                href={ad.snapshot_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline flex items-center gap-1 shrink-0 ml-2"
                              >
                                View
                                <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                          {ad.creative_body && (
                            <p className="text-muted-foreground line-clamp-2">
                              {ad.creative_body}
                            </p>
                          )}
                          <div className="flex items-center gap-3 text-muted-foreground">
                            {ad.start_date && (
                              <span>Started: {new Date(ad.start_date).toLocaleDateString()}</span>
                            )}
                            {ad.platforms && ad.platforms.length > 0 && (
                              <span>
                                Platforms: {ad.platforms.join(', ')}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {adLibrary?.error && adLibrary.error !== 'no_access_token' && (
                    <p className="text-xs text-amber-500">
                      API note: {adLibrary.error}
                    </p>
                  )}

                  {/* Search URL link */}
                  {adLibrary?.search_url && (
                    <a
                      href={adLibrary.search_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-primary hover:underline"
                    >
                      <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                      View in Meta Ad Library
                    </a>
                  )}
                </div>

                {/* Quick Links */}
                <div className="flex items-center gap-2">
                  <a
                    href={getMetaAdsLibraryUrl(scanResult?.fb_page_name || scanResult?.ad_library?.page_name || newCompetitor.name, newCompetitor.country, newCompetitor.fb_page_name)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 transition-colors"
                  >
                    <span className="font-bold">M</span>
                    Meta Ad Library
                    <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                  </a>
                  <a
                    href={getGoogleTransparencyUrl(newCompetitor.domain, newCompetitor.country)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-green-500/10 text-green-600 hover:bg-green-500/20 transition-colors"
                  >
                    <span className="font-bold">G</span>
                    Google Transparency
                    <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-muted/30 shrink-0">
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
                Add & Track
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddCompetitorModal;
