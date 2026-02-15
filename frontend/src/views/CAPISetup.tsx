/**
 * Integrations Page
 * No-code platform connection wizard for streaming first-party data
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Check,
  ChevronRight,
  ExternalLink,
  HelpCircle,
  Loader2,
  Play,
  Plug,
  RefreshCw,
  Settings,
  Shield,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiClient } from '@/api/client';

// Platform configurations
const PLATFORMS = [
  {
    id: 'meta',
    name: 'Meta (Facebook)',
    logo: '/platforms/meta.svg',
    color: 'bg-blue-500',
    description: 'Facebook & Instagram Conversion API',
    credentials: [
      {
        field: 'app_id',
        label: 'App ID',
        placeholder: '123456789012345',
        help: 'Found in Meta for Developers > Your App > Settings > Basic. This is your Meta App ID.',
      },
      {
        field: 'app_secret',
        label: 'App Secret',
        placeholder: '',
        help: 'Found in Meta for Developers > Your App > Settings > Basic. Click "Show" to reveal your App Secret.',
        sensitive: true,
      },
      {
        field: 'access_token',
        label: 'Access Token',
        placeholder: 'EAABsbCS...',
        help: 'System User Token from Business Settings > System Users > Generate Token. Required permissions: ads_management, ads_read.',
        sensitive: true,
      },
      {
        field: 'ad_account_ids',
        label: 'Ad Account IDs',
        placeholder: 'act_123456789, act_987654321',
        help: 'Comma-separated list of Ad Account IDs. Found in Ads Manager > Account Settings. Each starts with "act_" followed by numbers.',
      },
      {
        field: 'capi_access_token',
        label: 'CAPI Access Token',
        placeholder: 'EAABsbCS...',
        help: 'Dedicated Conversions API token. Go to Events Manager > Settings > Generate Access Token. Can be the same as Access Token if using a System User.',
        sensitive: true,
      },
      {
        field: 'pixel_id',
        label: 'Pixel ID',
        placeholder: '123456789012345',
        help: 'Found in Events Manager > Data Sources > Your Pixel. This is the 15-16 digit number associated with your Meta Pixel.',
      },
    ],
  },
  {
    id: 'google',
    name: 'Google Ads',
    logo: '/platforms/google.svg',
    color: 'bg-red-500',
    description: 'Google Ads & Enhanced Conversions',
    credentials: [
      {
        field: 'developer_token',
        label: 'Developer Token',
        placeholder: '',
        help: 'Found in Google Ads API Center (Tools > Setup > API Center). Required for server-to-server API calls.',
        sensitive: true,
      },
      {
        field: 'client_id',
        label: 'Client ID',
        placeholder: '',
        help: 'OAuth 2.0 Client ID from Google Cloud Console > APIs & Services > Credentials.',
      },
      {
        field: 'client_secret',
        label: 'Client Secret',
        placeholder: '',
        help: 'OAuth 2.0 Client Secret from Google Cloud Console > APIs & Services > Credentials.',
        sensitive: true,
      },
      {
        field: 'refresh_token',
        label: 'Refresh Token',
        placeholder: '1//0abc...',
        help: 'OAuth 2.0 refresh token. Generate via Google OAuth Playground or your app. Scopes: https://www.googleapis.com/auth/adwords',
        sensitive: true,
      },
      {
        field: 'access_token',
        label: 'Access Token',
        placeholder: '',
        help: 'OAuth 2.0 access token. Auto-refreshed using Refresh Token, but can be provided for initial setup.',
        sensitive: true,
      },
      {
        field: 'customer_id',
        label: 'Customer ID',
        placeholder: '1234567890',
        help: 'Your Google Ads Customer ID (10 digits). Found at the top of Google Ads dashboard next to your account name.',
      },
      {
        field: 'mcc_id',
        label: 'MCC ID (Manager Account)',
        placeholder: '1234567890',
        help: 'Manager (MCC) account ID. Required if managing multiple accounts under a manager account.',
      },
      {
        field: 'sub_account_ids',
        label: 'Sub-Account IDs',
        placeholder: '1234567890, 0987654321',
        help: 'Comma-separated list of sub-account Customer IDs under the MCC. Leave empty if not using sub-accounts.',
        optional: true,
      },
      {
        field: 'gtm_server_container',
        label: 'GTM Server Container',
        placeholder: 'GTM-XXXXXXX',
        help: 'Google Tag Manager Server-Side container ID. Found in GTM > Admin > Container Settings.',
        optional: true,
      },
      {
        field: 'gtm_web_container',
        label: 'GTM Web Container',
        placeholder: 'GTM-XXXXXXX',
        help: 'Google Tag Manager Web container ID. Found in GTM > Admin > Container Settings.',
        optional: true,
      },
      {
        field: 'ga4_measurement_id',
        label: 'GA4 Measurement ID',
        placeholder: 'G-XXXXXXXXXX',
        help: 'Found in Google Analytics > Admin > Data Streams > your web stream.',
        optional: true,
      },
      {
        field: 'tag_id',
        label: 'Tag ID',
        placeholder: '',
        help: 'Google Ads conversion tag ID. Found in Google Ads > Tools > Conversions.',
        optional: true,
      },
      {
        field: 'google_ads_id',
        label: 'Google Ads ID',
        placeholder: 'AW-XXXXXXXXX',
        help: 'Your Google Ads conversion tracking ID. Found in Google Ads > Tools > Conversions > Tag setup.',
        optional: true,
      },
    ],
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    logo: '/platforms/tiktok.svg',
    color: 'bg-black',
    description: 'TikTok Events API',
    credentials: [
      {
        field: 'app_id',
        label: 'App ID',
        placeholder: '',
        help: 'Found in TikTok for Business > Developer Portal > My Apps. Your TikTok marketing app identifier.',
      },
      {
        field: 'access_token',
        label: 'Access Token',
        placeholder: '',
        help: 'Long-lived access token from TikTok for Business. Go to Developer Portal > My Apps > Generate Token.',
        sensitive: true,
      },
      {
        field: 'app_secret',
        label: 'App Secret',
        placeholder: '',
        help: 'Found in TikTok for Business > Developer Portal > My Apps > your app settings.',
        sensitive: true,
      },
      {
        field: 'ad_account_id',
        label: 'Ad Account ID',
        placeholder: '',
        help: 'Found in TikTok Ads Manager > Account Settings. Your TikTok ad account number.',
      },
      {
        field: 'advertiser_id',
        label: 'Advertiser ID',
        placeholder: '7012345678901234567',
        help: 'Found at the top of TikTok Ads Manager dashboard. This is your advertiser-level identifier.',
      },
      {
        field: 'pixel_id',
        label: 'Pixel ID',
        placeholder: 'CXXXXXXXXXX',
        help: 'Found in TikTok Ads Manager > Events > Manage > Web Events. Starts with "C" followed by alphanumeric characters.',
      },
      {
        field: 'capi_token',
        label: 'CAPI Token',
        placeholder: '',
        help: 'Conversions API token from Events Manager > Manage > Settings > Generate Access Token. Required for server-side event delivery.',
        sensitive: true,
      },
    ],
  },
  {
    id: 'snapchat',
    name: 'Snapchat',
    logo: '/platforms/snapchat.svg',
    color: 'bg-yellow-400',
    description: 'Snapchat Conversion API',
    credentials: [
      {
        field: 'app_id',
        label: 'App ID',
        placeholder: '',
        help: 'Found in Snap Kit Developer Portal > Your App. Your Snapchat application identifier.',
      },
      {
        field: 'app_secret',
        label: 'App Secret',
        placeholder: '',
        help: 'Found in Snap Kit Developer Portal > Your App > OAuth2 settings.',
        sensitive: true,
      },
      {
        field: 'capi_token',
        label: 'CAPI Token',
        placeholder: '',
        help: 'Conversions API token from Snapchat Business Manager > Snap Pixel > Conversions API. Generate a long-lived token for server-side events.',
        sensitive: true,
      },
      {
        field: 'ad_account_id',
        label: 'Ad Account ID',
        placeholder: 'abc12345-1234-1234-1234-123456789012',
        help: 'Found in Ads Manager > Account Settings. This is your Snapchat ad account identifier.',
      },
      {
        field: 'pixel_id',
        label: 'Pixel ID',
        placeholder: 'abc12345-1234-1234-1234-123456789012',
        help: 'Found in Ads Manager > Events Manager > Snap Pixel. This is a UUID-format identifier for your Snap Pixel.',
      },
    ],
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp Business',
    logo: '/platforms/whatsapp.svg',
    color: 'bg-green-500',
    description: 'WhatsApp Business Cloud API',
    credentials: [
      {
        field: 'waba_id',
        label: 'WABA ID (WhatsApp Business Account ID)',
        placeholder: '317355655648785',
        help: 'Found in Meta Business Suite > WhatsApp Manager > Account Settings. Required to manage messaging and templates.',
      },
      {
        field: 'phone_number_id',
        label: 'Phone Number ID',
        placeholder: '966289803226237',
        help: 'The sending number identifier. Found in Meta Business Suite > WhatsApp Manager > Phone Numbers.',
      },
      {
        field: 'whatsapp_phone_number',
        label: 'WhatsApp Phone Number',
        placeholder: '00966512345678',
        help: 'Full phone number in international format: 00 + country code + phone number (e.g., 00966512345678 for Saudi Arabia).',
      },
      {
        field: 'meta_app_id',
        label: 'Meta App ID',
        placeholder: '123456789012345',
        help: 'The Meta App linked to the WhatsApp integration. Found in Meta for Developers > Your App > Settings > Basic.',
      },
      {
        field: 'graph_api_version',
        label: 'Graph API Version',
        placeholder: 'v24.0',
        help: 'The Graph API version your integration uses (e.g., v24.0). Check Meta for Developers for the latest supported version.',
      },
      {
        field: 'system_user_access_token',
        label: 'System User Access Token',
        placeholder: 'EAABsbCS...',
        help: 'Long-lived / permanent System User token with whatsapp_business_messaging and whatsapp_business_management permissions. Go to Business Settings > System Users > Generate Token.',
        sensitive: true,
      },
      {
        field: 'business_manager_id',
        label: 'Business Manager ID',
        placeholder: '123456789012345',
        help: 'Your Meta Business Manager ID. Found in Business Settings > Business Info. Helpful for multi-business setups.',
        optional: true,
      },
    ],
  },
];

interface PlatformStatus {
  connected: boolean;
  lastSync?: string;
  eventsToday?: number;
  matchQuality?: number;
}

interface TestResult {
  platform: string;
  status: 'success' | 'error';
  message: string;
}

export function CAPISetup() {
  const { t: _t } = useTranslation();
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);
  const [platformStatuses, setPlatformStatuses] = useState<Record<string, PlatformStatus>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTesting, setIsTesting] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[]>([]);

  // Fetch platform statuses
  useEffect(() => {
    fetchStatuses();
  }, []);

  const fetchStatuses = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/capi/platforms/status');
      const data = response.data;
      if (data.success) {
        const statuses: Record<string, PlatformStatus> = {};
        const connectedPlatforms = data.data?.connected_platforms || {};
        Object.keys(connectedPlatforms).forEach((platform) => {
          statuses[platform] = {
            connected: true,
            ...connectedPlatforms[platform],
          };
        });
        setPlatformStatuses(statuses);
      }
    } catch (err: any) {
      // Silenced - platforms may not be connected yet
      // Don't show error on initial load - platforms just aren't connected yet
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnect = async () => {
    if (!selectedPlatform) return;

    setConnecting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiClient.post('/capi/platforms/connect', {
        platform: selectedPlatform,
        credentials,
      });

      const data = response.data;

      if (data.success) {
        setSuccess(
          `Successfully connected to ${PLATFORMS.find((p) => p.id === selectedPlatform)?.name}!`
        );
        setPlatformStatuses((prev) => ({
          ...prev,
          [selectedPlatform]: { connected: true },
        }));
        setCredentials({});
        setSelectedPlatform(null);
      } else {
        setError(data.data?.message || 'Connection failed');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to connect. Please check your credentials.');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async (platform: string) => {
    try {
      const response = await apiClient.delete(`/capi/platforms/${platform}/disconnect`);
      const data = response.data;

      if (data.success) {
        setPlatformStatuses((prev) => {
          const updated = { ...prev };
          delete updated[platform];
          return updated;
        });
        setSuccess(`Disconnected from ${PLATFORMS.find((p) => p.id === platform)?.name}`);
      }
    } catch (err: any) {
      // Error displayed via setError below
      setError(err.response?.data?.detail || 'Failed to disconnect');
    }
  };

  const handleTestConnections = async () => {
    setIsTesting(true);
    setTestResults([]);
    try {
      const response = await apiClient.post('/capi/platforms/test');
      const data = response.data;

      if (data.success && data.data) {
        const results: TestResult[] = Object.entries(data.data).map(
          ([platform, result]: [string, any]) => ({
            platform,
            status: result.status === 'connected' ? 'success' : 'error',
            message:
              result.message ||
              (result.status === 'connected' ? 'Connection OK' : 'Connection failed'),
          })
        );
        setTestResults(results);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to test connections');
    } finally {
      setIsTesting(false);
    }
  };

  const connectedCount = Object.keys(platformStatuses).length;

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading integrations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Integrations</h1>
          <p className="text-muted-foreground mt-1">
            Connect ad platforms to stream first-party conversion data (purchases, leads, sign-ups)
            and boost ROAS by 30-50%
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connectedCount > 0 && (
            <button
              onClick={handleTestConnections}
              disabled={isTesting}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50"
            >
              {isTesting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Test Connections
            </button>
          )}
          <button
            onClick={fetchStatuses}
            className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Test Results */}
      {testResults.length > 0 && (
        <div className="rounded-xl border bg-card p-4">
          <h3 className="font-semibold mb-3">Connection Test Results</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {testResults.map((result) => (
              <div
                key={result.platform}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border',
                  result.status === 'success'
                    ? 'bg-green-500/5 border-green-500/20'
                    : 'bg-red-500/5 border-red-500/20'
                )}
              >
                {result.status === 'success' ? (
                  <Check className="w-5 h-5 text-green-500" />
                ) : (
                  <X className="w-5 h-5 text-red-500" />
                )}
                <div>
                  <span className="font-medium capitalize">{result.platform}</span>
                  <p className="text-xs text-muted-foreground">{result.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Benefits Banner */}
      <div className="bg-gradient-to-r from-primary/10 via-purple-500/10 to-pink-500/10 rounded-xl p-6 border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">70-90% Match Rates</h3>
              <p className="text-sm text-muted-foreground">Up from 42% with client-side tracking</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Shield className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Privacy-Compliant</h3>
              <p className="text-sm text-muted-foreground">Auto SHA256 hashing of PII data</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Zap className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">No Code Required</h3>
              <p className="text-sm text-muted-foreground">Just paste your API tokens</p>
            </div>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {success && (
        <div className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-600">
          <Check className="w-5 h-5" />
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Platform Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {PLATFORMS.map((platform) => {
          const status = platformStatuses[platform.id];
          const isSelected = selectedPlatform === platform.id;

          return (
            <div
              key={platform.id}
              className={cn(
                'relative rounded-xl border p-5 transition-all cursor-pointer',
                status?.connected
                  ? 'border-green-500/50 bg-green-500/5'
                  : isSelected
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50 hover:bg-muted/50'
              )}
              onClick={() =>
                !status?.connected && setSelectedPlatform(isSelected ? null : platform.id)
              }
            >
              {/* Connection Status Badge */}
              {status?.connected && (
                <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-1 bg-green-500/10 rounded-full">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs font-medium text-green-600">Connected</span>
                </div>
              )}

              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    'w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg',
                    platform.color
                  )}
                >
                  {platform.name.charAt(0)}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground">{platform.name}</h3>
                  <p className="text-sm text-muted-foreground">{platform.description}</p>
                </div>
              </div>

              {/* Credentials Form */}
              {isSelected && !status?.connected && (
                <div className="mt-4 pt-4 border-t space-y-3" onClick={(e) => e.stopPropagation()}>
                  {platform.credentials.map((cred) => (
                    <div key={cred.field}>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-sm font-medium text-foreground">
                          {cred.label}
                          {(cred as any).optional && (
                            <span className="text-xs font-normal text-muted-foreground ml-1.5">(optional)</span>
                          )}
                        </label>
                        <button
                          onClick={() => setShowHelp(showHelp === cred.field ? null : cred.field)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <HelpCircle className="w-4 h-4" />
                        </button>
                      </div>
                      {showHelp === cred.field && (
                        <p className="text-xs text-muted-foreground mb-2 bg-muted/50 p-2 rounded">
                          {cred.help}
                        </p>
                      )}
                      <input
                        type={cred.sensitive ? 'password' : 'text'}
                        placeholder={cred.placeholder}
                        value={credentials[cred.field] || ''}
                        onChange={(e) =>
                          setCredentials((prev) => ({ ...prev, [cred.field]: e.target.value }))
                        }
                        className="w-full px-3 py-2 border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      />
                    </div>
                  ))}

                  <button
                    onClick={handleConnect}
                    disabled={connecting || platform.credentials.filter((c) => !(c as any).optional).some((c) => !credentials[c.field])}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {connecting ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Plug className="w-4 h-4" />
                        Connect Platform
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Connected Actions */}
              {status?.connected && (
                <div
                  className="mt-4 pt-4 border-t flex items-center justify-between"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="text-sm">
                    <span className="text-muted-foreground">Events today:</span>
                    <span className="ml-2 font-semibold text-foreground">
                      {status.eventsToday || 0}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDisconnect(platform.id)}
                    className="text-sm text-red-500 hover:text-red-600 hover:underline"
                  >
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Setup Progress */}
      <div className="rounded-xl border bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Setup Progress</h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-green-500 transition-all duration-500"
                style={{ width: `${(connectedCount / PLATFORMS.length) * 100}%` }}
              />
            </div>
          </div>
          <div className="text-sm font-medium">
            <span className="text-primary">{connectedCount}</span>
            <span className="text-muted-foreground"> / {PLATFORMS.length} platforms</span>
          </div>
        </div>

        {connectedCount === 0 && (
          <p className="mt-4 text-sm text-muted-foreground">
            Connect at least one platform to start streaming conversion data
          </p>
        )}

        {connectedCount > 0 && connectedCount < PLATFORMS.length && (
          <p className="mt-4 text-sm text-muted-foreground">
            Connect more platforms to maximize your cross-channel attribution
          </p>
        )}

        {connectedCount === PLATFORMS.length && (
          <div className="mt-4 flex items-center gap-2 text-green-600">
            <Check className="w-5 h-5" />
            <span className="text-sm font-medium">All platforms connected!</span>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <a
          href="/dashboard/data-quality"
          className="flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Settings className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">Data Quality Dashboard</h3>
              <p className="text-sm text-muted-foreground">
                View match quality scores and fix data gaps
              </p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground" />
        </a>

        <a
          href="https://developers.facebook.com/docs/marketing-api/conversions-api"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <ExternalLink className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">Documentation</h3>
              <p className="text-sm text-muted-foreground">Learn more about Conversion APIs</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground" />
        </a>
      </div>
    </div>
  );
}

export default CAPISetup;
