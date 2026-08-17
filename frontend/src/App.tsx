import { Navigate, Route, Routes } from 'react-router-dom';
import { ComponentType, lazy } from 'react';
import { HelmetProvider } from 'react-helmet-async';
import DashboardLayout from './views/DashboardLayout';
import TenantLayout from './views/TenantLayout';
import { Toaster } from './components/ui/toaster';
import { TooltipProvider } from './components/ui/tooltip';
import { JoyrideProvider } from './components/guide/JoyrideWrapper';
import { ThemeProvider } from './components/primitives/theme/ThemeProvider';
import { AuthProvider } from './contexts/AuthContext';
import { DemoProvider } from './contexts/DemoContext';
import { UpgradePromptProvider } from './components/billing/UpgradePromptProvider';
import AuthLoader from './components/auth/AuthLoader';
import ProtectedRoute from './components/auth/ProtectedRoute';
import CMSProtectedRoute from './components/auth/CMSProtectedRoute';
import OnboardingGuard from './components/auth/OnboardingGuard';
import { SkipToContent } from './components/ui/skip-to-content';
import { useDocumentDirection } from './hooks/useDocumentDirection';
import { OfflineIndicator } from './components/common/OfflineIndicator';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import { LazyRoute } from './components/ui/LazyRoute';

// Component to handle document direction - must be inside i18n provider
function DocumentDirectionHandler() {
  useDocumentDirection();
  return null;
}

/**
 * Lazy import with automatic retry on chunk load failure.
 * After a new deploy, old chunk hashes no longer exist on the server.
 * This wrapper catches the import error and reloads the page once
 * so the browser fetches the fresh index.html with new chunk references.
 */
function lazyWithRetry(importFn: () => Promise<{ default: ComponentType<any> }>) {
  return lazy(() =>
    importFn().catch(() => {
      // Only auto-reload once to avoid infinite loops
      const reloaded = sessionStorage.getItem('chunk_reload');
      if (!reloaded) {
        sessionStorage.setItem('chunk_reload', '1');
        window.location.reload();
      }
      // Clear the flag after a short delay so future deploys also get retried
      setTimeout(() => sessionStorage.removeItem('chunk_reload'), 10000);
      // Re-throw so ErrorBoundary shows the error if reload didn't help
      return importFn();
    })
  );
}

// Lazy load pages for code splitting
const Landing = lazyWithRetry(() => import('./views/Landing'));
const LandingAr = lazyWithRetry(() => import('./views/LandingAr'));
const Login = lazyWithRetry(() => import('./views/Login'));
const Signup = lazyWithRetry(() => import('./views/Signup'));
const ForgotPassword = lazyWithRetry(() => import('./views/ForgotPassword'));
const ResetPassword = lazyWithRetry(() => import('./views/ResetPassword'));
const VerifyEmail = lazyWithRetry(() => import('./views/VerifyEmail'));
const Onboarding = lazyWithRetry(() => import('./views/Onboarding'));
const Overview = lazyWithRetry(() => import('./views/dashboard/Overview'));
const Plans = lazyWithRetry(() => import('./views/dashboard/Plans'));
const CustomDashboard = lazyWithRetry(() => import('./views/CustomDashboard'));
const Campaigns = lazyWithRetry(() => import('./views/Campaigns'));
const CampaignDetail = lazyWithRetry(() => import('./views/CampaignDetail'));
const Stratum = lazyWithRetry(() => import('./views/Stratum'));
const Benchmarks = lazyWithRetry(() => import('./views/Benchmarks'));
const Assets = lazyWithRetry(() => import('./views/Assets'));
const Rules = lazyWithRetry(() => import('./views/Rules'));
const Competitors = lazyWithRetry(() => import('./views/Competitors'));
const Predictions = lazyWithRetry(() => import('./views/Predictions'));
const EMQDiagnostics = lazyWithRetry(() => import('./views/EMQDiagnostics'));
const AIRecommendations = lazyWithRetry(() => import('./views/AIRecommendations'));
const WhatsApp = lazyWithRetry(() => import('./views/whatsapp/WhatsAppManager'));
const WhatsAppBroadcast = lazyWithRetry(() => import('./views/whatsapp/WhatsAppBroadcast'));
const WhatsAppContacts = lazyWithRetry(() => import('./views/whatsapp/WhatsAppContacts'));
const WhatsAppMessages = lazyWithRetry(() => import('./views/whatsapp/WhatsAppMessages'));
const WhatsAppTemplates = lazyWithRetry(() => import('./views/whatsapp/WhatsAppTemplates'));
const Settings = lazyWithRetry(() => import('./views/Settings'));
const Tenants = lazyWithRetry(() => import('./views/Tenants'));
const MLTraining = lazyWithRetry(() => import('./views/MLTraining'));
const CAPISetup = lazyWithRetry(() => import('./views/CAPISetup'));
const SuperadminDashboard = lazyWithRetry(() => import('./views/SuperadminDashboard'));
const ConsoleLayout = lazyWithRetry(() => import('./views/ConsoleLayout'));
const ConsoleFeatureFlags = lazyWithRetry(() => import('./views/console/FeatureFlags'));
const ConsolePlatformAnalytics = lazyWithRetry(() => import('./views/console/PlatformAnalytics'));
const ConsoleCredentials = lazyWithRetry(() => import('./views/console/Credentials'));
const ConsoleCrossTenantAnomalies = lazyWithRetry(
  () => import('./views/console/CrossTenantAnomalies')
);
const ConsoleAuditServices = lazyWithRetry(() => import('./views/console/AuditServices'));
const ConsoleEMQMeasure = lazyWithRetry(() => import('./views/console/EMQMeasureWorkflow'));
const ConsoleOfflineConversions = lazyWithRetry(() => import('./views/console/OfflineConversions'));
const ConsoleExperiments = lazyWithRetry(() => import('./views/console/Experiments'));
const ConsoleBudgetReallocation = lazyWithRetry(() => import('./views/console/BudgetReallocation'));
const ConsoleLTVBatch = lazyWithRetry(() => import('./views/console/LTVBatchPredict'));
const CDPCalculator = lazyWithRetry(() => import('./views/CDPCalculator'));

// CDP (Customer Data Platform) views
const CDPDashboard = lazyWithRetry(() => import('./views/cdp/CDPDashboard'));
const CDPProfiles = lazyWithRetry(() => import('./views/cdp/CDPProfiles'));
const CDPSegments = lazyWithRetry(() => import('./views/cdp/CDPSegments'));
const CDPEvents = lazyWithRetry(() => import('./views/cdp/CDPEvents'));
const CDPIdentityGraph = lazyWithRetry(() => import('./views/cdp/CDPIdentityGraph'));
const CDPAudienceSync = lazyWithRetry(() => import('./views/cdp/CDPAudienceSync'));
const CDPRfm = lazyWithRetry(() => import('./views/cdp/CDPRfm'));
const CDPFunnels = lazyWithRetry(() => import('./views/cdp/CDPFunnels'));
const CDPComputedTraits = lazyWithRetry(() => import('./views/cdp/CDPComputedTraits'));
const CDPConsent = lazyWithRetry(() => import('./views/cdp/CDPConsent'));
const CDPPredictiveChurn = lazyWithRetry(() => import('./views/cdp/CDPPredictiveChurn'));
// Tenant-scoped anomaly detection dashboard (rendered at /dashboard/anomalies)
const AnomalyDashboard = lazyWithRetry(() => import('./components/cdp/AnomalyDashboard'));

// Newsletter / Email Campaigns views
const NewsletterDashboard = lazyWithRetry(() => import('./views/newsletter/NewsletterDashboard'));
const NewsletterCampaigns = lazyWithRetry(() => import('./views/newsletter/NewsletterCampaigns'));
const NewsletterCampaignEditor = lazyWithRetry(
  () => import('./views/newsletter/NewsletterCampaignEditor')
);
const NewsletterTemplates = lazyWithRetry(() => import('./views/newsletter/NewsletterTemplates'));
const NewsletterSubscribers = lazyWithRetry(
  () => import('./views/newsletter/NewsletterSubscribers')
);
const NewsletterAnalytics = lazyWithRetry(() => import('./views/newsletter/NewsletterAnalytics'));

// Knowledge Graph views
const KnowledgeGraphInsights = lazyWithRetry(() => import('./views/KnowledgeGraphInsights'));
const KGProblemDetection = lazyWithRetry(
  () => import('./views/knowledge-graph/KGProblemDetection')
);
const KGRevenueAttribution = lazyWithRetry(
  () => import('./views/knowledge-graph/KGRevenueAttribution')
);

// Super Admin views
const ControlTower = lazyWithRetry(() => import('./views/superadmin/ControlTower'));
const SuperAdminTenantsList = lazyWithRetry(() => import('./views/superadmin/TenantsList'));
const SuperAdminTenantProfile = lazyWithRetry(() => import('./views/superadmin/TenantProfile'));
const SuperAdminBenchmarks = lazyWithRetry(() => import('./views/superadmin/Benchmarks'));
const SuperAdminAudit = lazyWithRetry(() => import('./views/superadmin/Audit'));
const SuperAdminBilling = lazyWithRetry(() => import('./views/superadmin/Billing'));
const SuperAdminSystem = lazyWithRetry(() => import('./views/superadmin/System'));
// SuperAdminCMS removed — CMS is now a separate portal at /cms
const SuperAdminUsers = lazyWithRetry(() => import('./views/superadmin/Users'));
const SuperAdminLaunchReadiness = lazyWithRetry(() => import('./views/superadmin/LaunchReadiness'));

// CMS (Content Management System) - Separate Portal
const CMSLogin = lazyWithRetry(() => import('./views/CMSLogin'));
const CMSLayout = lazyWithRetry(() => import('./views/CMSLayout'));
const CMSDashboard = lazyWithRetry(() => import('./views/cms/CMSDashboard'));
const CMSPosts = lazyWithRetry(() => import('./views/cms/CMSPosts'));
const CMSPostEditor = lazyWithRetry(() => import('./views/cms/CMSPostEditor'));
const CMSPages = lazyWithRetry(() => import('./views/cms/CMSPages'));
const CMSCategories = lazyWithRetry(() => import('./views/cms/CMSCategories'));
const CMSAuthors = lazyWithRetry(() => import('./views/cms/CMSAuthors'));
const CMSContacts = lazyWithRetry(() => import('./views/cms/CMSContacts'));
const CMSLandingFeatures = lazyWithRetry(() => import('./views/cms/CMSLandingFeatures'));
const CMSLandingFAQ = lazyWithRetry(() => import('./views/cms/CMSLandingFAQ'));
const CMSLandingPricing = lazyWithRetry(() => import('./views/cms/CMSLandingPricing'));
const CMSSettingsView = lazyWithRetry(() => import('./views/cms/CMSSettings'));
const CMSUsers = lazyWithRetry(() => import('./views/cms/CMSUsers'));

// Tenant-scoped views (Campaign Builder)
const ConnectPlatforms = lazyWithRetry(() => import('./views/tenant/ConnectPlatforms'));
const AdAccounts = lazyWithRetry(() => import('./views/tenant/AdAccounts'));
const CampaignBuilder = lazyWithRetry(() => import('./views/tenant/CampaignBuilder'));
const CampaignDrafts = lazyWithRetry(() => import('./views/tenant/CampaignDrafts'));
const PublishLogs = lazyWithRetry(() => import('./views/tenant/PublishLogs'));
const TenantOverview = lazyWithRetry(() => import('./views/tenant/TenantOverview'));
const TenantCampaigns = lazyWithRetry(() => import('./views/tenant/TenantCampaigns'));
const TenantSettings = lazyWithRetry(() => import('./views/tenant/TenantSettings'));
const TeamManagement = lazyWithRetry(() => import('./views/tenant/TeamManagement'));
const TenantInsights = lazyWithRetry(() => import('./views/tenant/Insights'));
const TenantAuditLog = lazyWithRetry(() => import('./views/tenant/AuditLog'));

// Role-based tenant views
const TenantAdminOverview = lazyWithRetry(() => import('./views/tenant/Overview'));
const MediaBuyerConsole = lazyWithRetry(() => import('./views/tenant/Console'));
const SignalHub = lazyWithRetry(() => import('./views/tenant/SignalHub'));

// Sprint feature views
// IntegrationsHub is rendered from Settings → Integrations tab now;
// the bare /dashboard/integrations route just 302s there.
const GDPR = lazyWithRetry(() => import('./views/GDPR'));
const APIKeys = lazyWithRetry(() => import('./views/APIKeys'));
const Pacing = lazyWithRetry(() => import('./views/tenant/Pacing'));
const ProfitROAS = lazyWithRetry(() => import('./views/tenant/ProfitROAS'));
const Attribution = lazyWithRetry(() => import('./views/tenant/Attribution'));
const Reporting = lazyWithRetry(() => import('./views/tenant/Reporting'));

// P1 Feature views - A/B Testing, DLQ, Model Explainability
const ABTesting = lazyWithRetry(() => import('./views/tenant/ABTesting'));
const DeadLetterQueue = lazyWithRetry(() => import('./views/tenant/DeadLetterQueue'));
const ModelExplainability = lazyWithRetry(() => import('./views/tenant/ModelExplainability'));

// Enterprise feature views
const CustomAutopilotRules = lazyWithRetry(() => import('./views/CustomAutopilotRules'));
const CustomReportBuilder = lazyWithRetry(() => import('./views/CustomReportBuilder'));

// Embed Widgets
const EmbedWidgets = lazyWithRetry(() => import('./views/tenant/EmbedWidgets'));

// Account Manager views
const AMPortfolio = lazyWithRetry(() => import('./views/am/Portfolio'));
const AMTenantNarrative = lazyWithRetry(() => import('./views/am/TenantNarrative'));

// Portal views (client VIEWER users)
const PortalLayout = lazyWithRetry(() => import('./views/portal/PortalLayout'));
const PortalDashboard = lazyWithRetry(() => import('./views/portal/PortalDashboard'));

// Accept Invite (portal user onboarding)
const AcceptInvite = lazyWithRetry(() => import('./views/AcceptInvite'));

// Client Assignments (admin UI)
const ClientAssignments = lazyWithRetry(() => import('./views/tenant/ClientAssignments'));

// Tier-specific landing pages
const TierLandingPage = lazyWithRetry(() => import('./views/plans/TierLandingPage'));

// Public pages (Product)
const FeaturesPage = lazyWithRetry(() => import('./views/pages/Features'));
const PricingPage = lazyWithRetry(() => import('./views/pages/Pricing'));
const IntegrationsPage = lazyWithRetry(() => import('./views/pages/Integrations'));
const ApiDocsPage = lazyWithRetry(() => import('./views/pages/ApiDocs'));

// Public pages (Solutions)
const CDPSolutionPage = lazyWithRetry(() => import('./views/pages/solutions/CDP'));
const AudienceSyncPage = lazyWithRetry(() => import('./views/pages/solutions/AudienceSync'));
const PredictionsSolutionPage = lazyWithRetry(
  () => import('./views/pages/solutions/PredictionsSolution')
);
const TrustEnginePage = lazyWithRetry(() => import('./views/pages/solutions/TrustEngine'));

// Public pages (Company)
const AboutPage = lazyWithRetry(() => import('./views/pages/company/About'));
const CareersPage = lazyWithRetry(() => import('./views/pages/company/Careers'));
const BlogPage = lazyWithRetry(() => import('./views/pages/company/Blog'));
const BlogPostPage = lazyWithRetry(() => import('./views/pages/company/BlogPost'));
const ContactPage = lazyWithRetry(() => import('./views/pages/company/Contact'));
const FAQPage = lazyWithRetry(() => import('./views/pages/company/FAQ'));

// Public pages (Legal)
const PrivacyPage = lazyWithRetry(() => import('./views/pages/legal/Privacy'));
const TermsPage = lazyWithRetry(() => import('./views/pages/legal/Terms'));
const SecurityPage = lazyWithRetry(() => import('./views/pages/legal/Security'));
const DPAPage = lazyWithRetry(() => import('./views/pages/legal/DPA'));

// Public pages (Resources)
const DocsPage = lazyWithRetry(() => import('./views/pages/resources/Docs'));
const DocArticlePage = lazyWithRetry(
  () => import('./views/pages/resources/docs/DocArticlePage')
);
const ChangelogPage = lazyWithRetry(() => import('./views/pages/resources/Changelog'));
const CaseStudiesPage = lazyWithRetry(() => import('./views/pages/resources/CaseStudies'));
const ResourcesPage = lazyWithRetry(() => import('./views/pages/resources/Resources'));
const StatusPage = lazyWithRetry(() => import('./views/pages/resources/Status'));
const ComparisonPage = lazyWithRetry(() => import('./views/pages/resources/Comparison'));
const GlossaryPage = lazyWithRetry(() => import('./views/pages/resources/Glossary'));
const NotFound = lazyWithRetry(() => import('./views/NotFound'));
const Unauthorized = lazyWithRetry(() => import('./views/Unauthorized'));

// Checkout flow
const CheckoutPage = lazyWithRetry(() => import('./views/checkout/CheckoutPage'));
const CheckoutSuccess = lazyWithRetry(() => import('./views/checkout/CheckoutSuccess'));
const CheckoutCancel = lazyWithRetry(() => import('./views/checkout/CheckoutCancel'));

// Announcement pages
const AudienceSyncLaunch = lazyWithRetry(
  () => import('./views/pages/announcements/AudienceSyncLaunch')
);

// Gap implementation views
const AIInsights = lazyWithRetry(() => import('./views/AIInsights'));
const FunnelAnalysis = lazyWithRetry(() => import('./views/FunnelAnalysis'));
const CohortAnalysis = lazyWithRetry(() => import('./views/CohortAnalysis'));
const SQLEditor = lazyWithRetry(() => import('./views/SQLEditor'));
const ComplianceDashboard = lazyWithRetry(() => import('./views/ComplianceDashboard'));
const IntegrationHub = lazyWithRetry(() => import('./views/IntegrationHub'));
const DeveloperPortal = lazyWithRetry(() => import('./views/DeveloperPortal'));

// Drip Campaigns & Push Notifications
const DripCampaignBuilder = lazyWithRetry(() => import('./views/DripCampaignBuilder'));
const PushNotifications = lazyWithRetry(() => import('./views/PushNotifications'));

function App() {
  return (
    <HelmetProvider>
      <ThemeProvider>
        <AuthProvider>
          <DemoProvider>
            <TooltipProvider delayDuration={300}>
              <JoyrideProvider>
                <UpgradePromptProvider>
                  {/* Sync HTML lang/dir with i18n */}
                  <DocumentDirectionHandler />
                  {/* Skip to content link for keyboard accessibility */}
                  <SkipToContent />
                  <div className="min-h-screen bg-background" id="main-content" role="main">
                    <Routes>
                      {/* Public routes — Landing (BUG-015: wrapped with ErrorBoundary) */}
                      <Route
                        path="/"
                        element={
                          <ErrorBoundary message="Failed to load the landing page">
                            <LazyRoute>
                              <Landing />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/ar"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <LandingAr />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/login"
                        element={
                          <ErrorBoundary message="Failed to load the login page">
                            <LazyRoute fallback={<AuthLoader />}>
                              <Login />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/signup"
                        element={
                          <ErrorBoundary message="Failed to load the signup page">
                            <LazyRoute fallback={<AuthLoader />}>
                              <Signup />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/forgot-password"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute fallback={<AuthLoader />}>
                              <ForgotPassword />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/reset-password"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute fallback={<AuthLoader />}>
                              <ResetPassword />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/verify-email"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute fallback={<AuthLoader />}>
                              <VerifyEmail />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />

                      {/* Accept Invite (public - portal user onboarding) */}
                      <Route
                        path="/accept-invite"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <AcceptInvite />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />

                      {/* CMS Login (public) */}
                      <Route
                        path="/cms-login"
                        element={
                          <LazyRoute>
                            <CMSLogin />
                          </LazyRoute>
                        }
                      />

                      {/* CMS Portal (protected - requires cms_role) */}
                      <Route
                        path="/cms"
                        element={
                          <CMSProtectedRoute>
                            <LazyRoute>
                              <CMSLayout />
                            </LazyRoute>
                          </CMSProtectedRoute>
                        }
                      >
                        <Route
                          index
                          element={
                            <LazyRoute>
                              <CMSDashboard />
                            </LazyRoute>
                          }
                        />
                        {/* Posts Management */}
                        <Route
                          path="posts"
                          element={
                            <LazyRoute>
                              <CMSPosts />
                            </LazyRoute>
                          }
                        />
                        {/* Post Create */}
                        <Route
                          path="posts/new"
                          element={
                            <LazyRoute>
                              <CMSPostEditor />
                            </LazyRoute>
                          }
                        />
                        {/* Post Edit */}
                        <Route
                          path="posts/:id"
                          element={
                            <LazyRoute>
                              <CMSPostEditor />
                            </LazyRoute>
                          }
                        />
                        {/* Categories Management */}
                        <Route
                          path="categories"
                          element={
                            <LazyRoute>
                              <CMSCategories />
                            </LazyRoute>
                          }
                        />
                        {/* Authors Management */}
                        <Route
                          path="authors"
                          element={
                            <LazyRoute>
                              <CMSAuthors />
                            </LazyRoute>
                          }
                        />
                        {/* Contact Submissions */}
                        <Route
                          path="contacts"
                          element={
                            <LazyRoute>
                              <CMSContacts />
                            </LazyRoute>
                          }
                        />
                        {/* Pages Management */}
                        <Route
                          path="pages"
                          element={
                            <LazyRoute>
                              <CMSPages />
                            </LazyRoute>
                          }
                        />
                        {/* Landing Content - Features */}
                        <Route
                          path="landing/features"
                          element={
                            <LazyRoute>
                              <CMSLandingFeatures />
                            </LazyRoute>
                          }
                        />
                        {/* Landing Content - FAQ */}
                        <Route
                          path="landing/faq"
                          element={
                            <LazyRoute>
                              <CMSLandingFAQ />
                            </LazyRoute>
                          }
                        />
                        {/* Landing Content - Pricing */}
                        <Route
                          path="landing/pricing"
                          element={
                            <LazyRoute>
                              <CMSLandingPricing />
                            </LazyRoute>
                          }
                        />
                        {/* CMS Settings */}
                        <Route
                          path="settings"
                          element={
                            <LazyRoute>
                              <CMSSettingsView />
                            </LazyRoute>
                          }
                        />
                        {/* CMS User Management */}
                        <Route
                          path="users"
                          element={
                            <LazyRoute
                              fallback={
                                <div className="flex items-center justify-center min-h-screen">
                                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400" />
                                </div>
                              }
                            >
                              <CMSUsers />
                            </LazyRoute>
                          }
                        />
                      </Route>

                      {/* CDP ROI Calculator (public) */}
                      <Route
                        path="/cdp-calculator"
                        element={
                          <LazyRoute>
                            <CDPCalculator />
                          </LazyRoute>
                        }
                      />

                      {/* Tier-specific landing pages (public) */}
                      <Route
                        path="/plans/:tier"
                        element={
                          <LazyRoute>
                            <TierLandingPage />
                          </LazyRoute>
                        }
                      />

                      {/* Product pages (public) */}
                      <Route
                        path="/features"
                        element={
                          <LazyRoute>
                            <FeaturesPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/pricing"
                        element={
                          <LazyRoute>
                            <PricingPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/integrations"
                        element={
                          <LazyRoute>
                            <IntegrationsPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/api-docs"
                        element={
                          <LazyRoute>
                            <ApiDocsPage />
                          </LazyRoute>
                        }
                      />

                      {/* Solutions pages (public) */}
                      <Route
                        path="/solutions/cdp"
                        element={
                          <LazyRoute>
                            <CDPSolutionPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/solutions/audience-sync"
                        element={
                          <LazyRoute>
                            <AudienceSyncPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/solutions/predictions"
                        element={
                          <LazyRoute>
                            <PredictionsSolutionPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/solutions/trust-engine"
                        element={
                          <LazyRoute>
                            <TrustEnginePage />
                          </LazyRoute>
                        }
                      />

                      {/* Company pages (public) */}
                      <Route
                        path="/about"
                        element={
                          <LazyRoute>
                            <AboutPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/careers"
                        element={
                          <LazyRoute>
                            <CareersPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/blog"
                        element={
                          <LazyRoute>
                            <BlogPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/blog/:slug"
                        element={
                          <LazyRoute>
                            <BlogPostPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/contact"
                        element={
                          <LazyRoute>
                            <ContactPage />
                          </LazyRoute>
                        }
                      />
                      <Route
                        path="/faq"
                        element={
                          <LazyRoute>
                            <FAQPage />
                          </LazyRoute>
                        }
                      />

                      {/* Legal pages (public) */}
                      <Route
                        path="/privacy"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <PrivacyPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/terms"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <TermsPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/security"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <SecurityPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/dpa"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <DPAPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />

                      {/* Resources pages (public) */}
                      <Route
                        path="/docs"
                        element={
                          <ErrorBoundary message="Failed to load the documentation page">
                            <LazyRoute>
                              <DocsPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/docs/*"
                        element={
                          <ErrorBoundary message="Failed to load the documentation page">
                            <LazyRoute>
                              <DocArticlePage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/changelog"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <ChangelogPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/case-studies"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <CaseStudiesPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/resources"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <ResourcesPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/status"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <StatusPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/compare"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <ComparisonPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />
                      <Route
                        path="/glossary"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <GlossaryPage />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />

                      {/* Announcement pages */}
                      <Route
                        path="/announcements/audience-sync"
                        element={
                          <ErrorBoundary message="Failed to load the page">
                            <LazyRoute>
                              <AudienceSyncLaunch />
                            </LazyRoute>
                          </ErrorBoundary>
                        }
                      />

                      {/* Client Portal routes (portal/VIEWER users only) */}
                      <Route
                        path="/portal"
                        element={
                          <ProtectedRoute portalOnly>
                            <LazyRoute>
                              <PortalLayout />
                            </LazyRoute>
                          </ProtectedRoute>
                        }
                      >
                        <Route
                          index
                          element={
                            <LazyRoute>
                              <PortalDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns"
                          element={
                            <LazyRoute>
                              <PortalDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="requests"
                          element={
                            <LazyRoute>
                              <PortalDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="profile"
                          element={
                            <LazyRoute>
                              <Settings />
                            </LazyRoute>
                          }
                        />
                      </Route>

                      {/* Onboarding wizard (protected) */}
                      <Route
                        path="/onboarding"
                        element={
                          <ProtectedRoute>
                            <LazyRoute>
                              <Onboarding />
                            </LazyRoute>
                          </ProtectedRoute>
                        }
                      />

                      {/* Checkout flow (protected) */}
                      <Route
                        path="/checkout"
                        element={
                          <ProtectedRoute>
                            <LazyRoute>
                              <CheckoutPage />
                            </LazyRoute>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/checkout/success"
                        element={
                          <ProtectedRoute>
                            <LazyRoute>
                              <CheckoutSuccess />
                            </LazyRoute>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/checkout/cancel"
                        element={
                          <ProtectedRoute>
                            <LazyRoute>
                              <CheckoutCancel />
                            </LazyRoute>
                          </ProtectedRoute>
                        }
                      />

                      {/* Protected dashboard routes - wrapped with onboarding guard + ErrorBoundary */}
                      <Route
                        path="/dashboard"
                        element={
                          <ProtectedRoute>
                            <OnboardingGuard>
                              <ErrorBoundary message="Something went wrong in the dashboard. Please try refreshing.">
                                <DashboardLayout />
                              </ErrorBoundary>
                            </OnboardingGuard>
                          </ProtectedRoute>
                        }
                      >
                        <Route index element={<Navigate to="/dashboard/overview" replace />} />
                        {/* Sidebar links from earlier IA pointed at URLs without
                            backing routes. Redirect to the real destinations so
                            old bookmarks don't 404. */}
                        <Route
                          path="autopilot"
                          element={<Navigate to="/dashboard/rules" replace />}
                        />
                        <Route
                          path="audiences"
                          element={<Navigate to="/dashboard/cdp/audience-sync" replace />}
                        />
                        <Route
                          path="trust-engine"
                          element={<Navigate to="/dashboard/trust" replace />}
                        />
                        <Route
                          path="overview"
                          element={
                            <LazyRoute>
                              <Overview />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="plans"
                          element={
                            <LazyRoute>
                              <Plans />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="custom-dashboard"
                          element={
                            <LazyRoute>
                              <CustomDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns"
                          element={
                            <LazyRoute>
                              <Campaigns />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns/:id"
                          element={
                            <LazyRoute>
                              <CampaignDetail />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="stratum"
                          element={
                            <LazyRoute>
                              <Stratum />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="benchmarks"
                          element={
                            <LazyRoute>
                              <Benchmarks />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="assets"
                          element={
                            <LazyRoute>
                              <Assets />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="rules"
                          element={
                            <LazyRoute>
                              <Rules />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="competitors"
                          element={
                            <LazyRoute>
                              <Competitors />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="predictions"
                          element={
                            <LazyRoute>
                              <Predictions />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="whatsapp"
                          element={
                            <LazyRoute>
                              <WhatsApp />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="whatsapp/broadcast"
                          element={
                            <LazyRoute>
                              <WhatsAppBroadcast />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="whatsapp/contacts"
                          element={
                            <LazyRoute>
                              <WhatsAppContacts />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="whatsapp/messages"
                          element={
                            <LazyRoute>
                              <WhatsAppMessages />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="whatsapp/templates"
                          element={
                            <LazyRoute>
                              <WhatsAppTemplates />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="settings"
                          element={<Navigate to="/dashboard/settings/profile" replace />}
                        />
                        <Route
                          path="settings/:tab"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <Settings />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="tenants"
                          element={
                            <LazyRoute>
                              <Tenants />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="ml-training"
                          element={
                            <LazyRoute>
                              <MLTraining />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="capi-setup"
                          element={
                            <LazyRoute>
                              <CAPISetup />
                            </LazyRoute>
                          }
                        />

                        {/* Signal Hub (EMQ / Signal Health) */}
                        <Route
                          path="signal-hub"
                          element={
                            <LazyRoute>
                              <SignalHub />
                            </LazyRoute>
                          }
                        />

                        {/* CDP (Customer Data Platform) routes */}
                        <Route
                          path="cdp"
                          element={
                            <LazyRoute>
                              <CDPDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/profiles"
                          element={
                            <LazyRoute>
                              <CDPProfiles />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/segments"
                          element={
                            <LazyRoute>
                              <CDPSegments />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/events"
                          element={
                            <LazyRoute>
                              <CDPEvents />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/identity"
                          element={
                            <LazyRoute>
                              <CDPIdentityGraph />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/audience-sync"
                          element={
                            <LazyRoute>
                              <CDPAudienceSync />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/rfm"
                          element={
                            <LazyRoute>
                              <CDPRfm />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/funnels"
                          element={
                            <LazyRoute>
                              <CDPFunnels />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/computed-traits"
                          element={
                            <LazyRoute>
                              <CDPComputedTraits />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/consent"
                          element={
                            <LazyRoute>
                              <CDPConsent />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="cdp/predictive-churn"
                          element={
                            <LazyRoute>
                              <CDPPredictiveChurn />
                            </LazyRoute>
                          }
                        />

                        {/* Newsletter / Email Campaign routes */}
                        <Route
                          path="newsletter"
                          element={
                            <LazyRoute>
                              <NewsletterDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="newsletter/campaigns"
                          element={
                            <LazyRoute>
                              <NewsletterCampaigns />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="newsletter/campaigns/new"
                          element={
                            <LazyRoute>
                              <NewsletterCampaignEditor />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="newsletter/campaigns/:id/edit"
                          element={
                            <LazyRoute>
                              <NewsletterCampaignEditor />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="newsletter/campaigns/:id/analytics"
                          element={
                            <LazyRoute>
                              <NewsletterAnalytics />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="newsletter/templates"
                          element={
                            <LazyRoute>
                              <NewsletterTemplates />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="newsletter/subscribers"
                          element={
                            <LazyRoute>
                              <NewsletterSubscribers />
                            </LazyRoute>
                          }
                        />

                        {/* Knowledge Graph routes */}
                        <Route
                          path="knowledge-graph"
                          element={
                            <LazyRoute>
                              <KnowledgeGraphInsights />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="knowledge-graph/insights"
                          element={
                            <LazyRoute>
                              <KnowledgeGraphInsights />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="knowledge-graph/problems"
                          element={
                            <LazyRoute>
                              <KGProblemDetection />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="knowledge-graph/revenue"
                          element={
                            <LazyRoute>
                              <KGRevenueAttribution />
                            </LazyRoute>
                          }
                        />

                        {/* Enterprise feature routes (admin+ only) */}
                        <Route
                          path="custom-autopilot-rules"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <CustomAutopilotRules />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="custom-reports"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <CustomReportBuilder />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Gap implementation routes */}
                        <Route
                          path="ai-insights"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <AIInsights />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="ai-recommendations"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <AIRecommendations />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="funnel-analysis"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <FunnelAnalysis />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="cohort-analysis"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <CohortAnalysis />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="sql-editor"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <SQLEditor />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="compliance"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <ComplianceDashboard />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="gdpr"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <GDPR />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="api-keys"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <APIKeys />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="integration-hub"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <IntegrationHub />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="developer"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <DeveloperPortal />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Drip Campaigns & Push Notifications */}
                        <Route
                          path="drip-campaigns"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <DripCampaignBuilder />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="push-notifications"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <PushNotifications />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Operator-dashboard surfaces for tenant-scoped
                            features. These views resolve their tenant from
                            context (not the URL), so the sidebar's static
                            /dashboard/* hrefs render them directly here —
                            mirroring the /app/:tenantId/* twins below. Without
                            these, the sidebar links fell through to the `*`
                            catch-all and 404'd. */}
                        <Route
                          path="trust"
                          element={
                            <LazyRoute>
                              <TenantAdminOverview />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="trust/emq"
                          element={
                            <LazyRoute>
                              <EMQDiagnostics />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="pacing"
                          element={
                            <LazyRoute>
                              <Pacing />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="profit"
                          element={
                            <LazyRoute>
                              <ProfitROAS />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="attribution"
                          element={
                            <LazyRoute>
                              <Attribution />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="reporting"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <Reporting />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="ab-testing"
                          element={
                            <LazyRoute>
                              <ABTesting />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="anomalies"
                          element={
                            <LazyRoute>
                              <AnomalyDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="explainability"
                          element={
                            <LazyRoute>
                              <ModelExplainability />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="embed-widgets"
                          element={
                            <LazyRoute>
                              <EmbedWidgets />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="audit-log"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <TenantAuditLog />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="team"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <TeamManagement />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Superadmin routes moved to /console/* shell.
                            Sibling-level redirects from /dashboard/superadmin/*
                            preserve old links. See route block below the
                            dashboard route closer. */}

                        {/* Account Manager routes */}
                        <Route
                          path="am/portfolio"
                          element={
                            <LazyRoute>
                              <AMPortfolio />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="am/tenant/:tenantId"
                          element={
                            <LazyRoute>
                              <AMTenantNarrative />
                            </LazyRoute>
                          }
                        />
                      </Route>

                      {/* Tenant-scoped routes with :tenantId parameter - wrapped with onboarding guard + ErrorBoundary */}
                      <Route
                        path="/app/:tenantId"
                        element={
                          <ProtectedRoute>
                            <OnboardingGuard>
                              <ErrorBoundary message="Something went wrong. Please try refreshing.">
                                <TenantLayout />
                              </ErrorBoundary>
                            </OnboardingGuard>
                          </ProtectedRoute>
                        }
                      >
                        {/* Tenant Dashboard */}
                        <Route
                          index
                          element={
                            <LazyRoute>
                              <TenantOverview />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="overview"
                          element={
                            <LazyRoute>
                              <TenantOverview />
                            </LazyRoute>
                          }
                        />

                        {/* Role-based views */}
                        <Route
                          path="trust"
                          element={
                            <LazyRoute>
                              <TenantAdminOverview />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="trust/emq"
                          element={
                            <LazyRoute>
                              <EMQDiagnostics />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="console"
                          element={
                            <LazyRoute>
                              <MediaBuyerConsole />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="signal-hub"
                          element={
                            <LazyRoute>
                              <SignalHub />
                            </LazyRoute>
                          }
                        />

                        {/* Campaigns Management */}
                        <Route
                          path="campaigns"
                          element={
                            <LazyRoute>
                              <TenantCampaigns />
                            </LazyRoute>
                          }
                        />

                        {/* Campaign Builder Routes */}
                        <Route
                          path="campaigns/connect"
                          element={
                            <LazyRoute>
                              <ConnectPlatforms />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns/accounts"
                          element={
                            <LazyRoute>
                              <AdAccounts />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns/new"
                          element={
                            <LazyRoute>
                              <CampaignBuilder />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns/drafts"
                          element={
                            <LazyRoute>
                              <CampaignDrafts />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns/drafts/:draftId"
                          element={
                            <LazyRoute>
                              <CampaignBuilder />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="campaigns/logs"
                          element={
                            <LazyRoute>
                              <PublishLogs />
                            </LazyRoute>
                          }
                        />

                        {/* Tenant Settings (admin+ only) */}
                        <Route
                          path="settings"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <TenantSettings />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Team Management (admin+ only) */}
                        <Route
                          path="team"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <TeamManagement />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Client Assignments (admin+ only) */}
                        <Route
                          path="client-assignments"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <ClientAssignments />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Tenant Insights (manager+ only) */}
                        <Route
                          path="insights"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <TenantInsights />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Tenant Audit Log (admin+ only) */}
                        <Route
                          path="audit-log"
                          element={
                            <ProtectedRoute requiredRole="admin">
                              <LazyRoute>
                                <TenantAuditLog />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* Competitors */}
                        <Route
                          path="competitors"
                          element={
                            <LazyRoute>
                              <Competitors />
                            </LazyRoute>
                          }
                        />

                        {/* Benchmarks */}
                        <Route
                          path="benchmarks"
                          element={
                            <LazyRoute>
                              <Benchmarks />
                            </LazyRoute>
                          }
                        />

                        {/* Assets */}
                        <Route
                          path="assets"
                          element={
                            <LazyRoute>
                              <Assets />
                            </LazyRoute>
                          }
                        />

                        {/* Rules */}
                        <Route
                          path="rules"
                          element={
                            <LazyRoute>
                              <Rules />
                            </LazyRoute>
                          }
                        />

                        {/* Predictions */}
                        <Route
                          path="predictions"
                          element={
                            <LazyRoute>
                              <Predictions />
                            </LazyRoute>
                          }
                        />

                        {/* Sprint Feature Routes */}
                        {/* Integrations is the canonical surface inside Settings.
                            Old /dashboard/integrations redirects so bookmarks
                            and the IntegrationsHub's "Open hub" links stay valid. */}
                        <Route
                          path="integrations"
                          element={<Navigate to="/dashboard/settings/integrations" replace />}
                        />

                        {/* Pacing & Forecasting */}
                        <Route
                          path="pacing"
                          element={
                            <LazyRoute>
                              <Pacing />
                            </LazyRoute>
                          }
                        />

                        {/* Profit ROAS */}
                        <Route
                          path="profit"
                          element={
                            <LazyRoute>
                              <ProfitROAS />
                            </LazyRoute>
                          }
                        />

                        {/* Attribution */}
                        <Route
                          path="attribution"
                          element={
                            <LazyRoute>
                              <Attribution />
                            </LazyRoute>
                          }
                        />

                        {/* Reporting (manager+ only) */}
                        <Route
                          path="reporting"
                          element={
                            <ProtectedRoute requiredRole="manager">
                              <LazyRoute>
                                <Reporting />
                              </LazyRoute>
                            </ProtectedRoute>
                          }
                        />

                        {/* A/B Testing */}
                        <Route
                          path="ab-testing"
                          element={
                            <LazyRoute>
                              <ABTesting />
                            </LazyRoute>
                          }
                        />

                        {/* Dead Letter Queue (CAPI) */}
                        <Route
                          path="dead-letter-queue"
                          element={
                            <LazyRoute>
                              <DeadLetterQueue />
                            </LazyRoute>
                          }
                        />

                        {/* Model Explainability (SHAP/LIME/LTV) */}
                        <Route
                          path="explainability"
                          element={
                            <LazyRoute>
                              <ModelExplainability />
                            </LazyRoute>
                          }
                        />

                        {/* Embed Widgets */}
                        <Route
                          path="embed-widgets"
                          element={
                            <LazyRoute>
                              <EmbedWidgets />
                            </LazyRoute>
                          }
                        />
                      </Route>

                      {/* ═══════════════════════════════════════════════
                           Platform Console — owner-only shell at /console/*
                           Distinct from operator dashboard. Reuses
                           existing superadmin/* views as their canonical
                           home. Old /dashboard/superadmin/* paths still
                           work (kept for back-compat).
                         ═══════════════════════════════════════════════ */}
                      <Route
                        path="/console"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <ErrorBoundary message="Something went wrong in the platform console. Please try refreshing.">
                              <LazyRoute>
                                <ConsoleLayout />
                              </LazyRoute>
                            </ErrorBoundary>
                          </ProtectedRoute>
                        }
                      >
                        <Route
                          index
                          element={
                            <LazyRoute>
                              <SuperadminDashboard />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="tenants"
                          element={
                            <LazyRoute>
                              <SuperAdminTenantsList />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="tenants/:tenantId"
                          element={
                            <LazyRoute>
                              <SuperAdminTenantProfile />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="users"
                          element={
                            <LazyRoute>
                              <SuperAdminUsers />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="feature-flags"
                          element={
                            <LazyRoute>
                              <ConsoleFeatureFlags />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="credentials"
                          element={
                            <LazyRoute>
                              <ConsoleCredentials />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="billing"
                          element={
                            <LazyRoute>
                              <SuperAdminBilling />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="control-tower"
                          element={
                            <LazyRoute>
                              <ControlTower />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="dead-letter-queue"
                          element={
                            <LazyRoute>
                              <DeadLetterQueue />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="publish-logs"
                          element={
                            <LazyRoute>
                              <PublishLogs />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="system"
                          element={
                            <LazyRoute>
                              <SuperAdminSystem />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="launch-readiness"
                          element={
                            <LazyRoute>
                              <SuperAdminLaunchReadiness />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="analytics"
                          element={
                            <LazyRoute>
                              <ConsolePlatformAnalytics />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="benchmarks"
                          element={
                            <LazyRoute>
                              <SuperAdminBenchmarks />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="audit"
                          element={
                            <LazyRoute>
                              <SuperAdminAudit />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="anomalies"
                          element={
                            <LazyRoute>
                              <ConsoleCrossTenantAnomalies />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="audit-services"
                          element={
                            <LazyRoute>
                              <ConsoleAuditServices />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="emq-measure"
                          element={
                            <LazyRoute>
                              <ConsoleEMQMeasure />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="offline-conversions"
                          element={
                            <LazyRoute>
                              <ConsoleOfflineConversions />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="experiments"
                          element={
                            <LazyRoute>
                              <ConsoleExperiments />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="budget-reallocation"
                          element={
                            <LazyRoute>
                              <ConsoleBudgetReallocation />
                            </LazyRoute>
                          }
                        />
                        <Route
                          path="ltv-batch"
                          element={
                            <LazyRoute>
                              <ConsoleLTVBatch />
                            </LazyRoute>
                          }
                        />
                      </Route>

                      {/* Legacy route redirects */}
                      <Route
                        path="/overview"
                        element={<Navigate to="/dashboard/overview" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin"
                        element={<Navigate to="/console" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/tenants"
                        element={<Navigate to="/console/tenants" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/users"
                        element={<Navigate to="/console/users" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/launch-readiness"
                        element={<Navigate to="/console/launch-readiness" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/control-tower"
                        element={<Navigate to="/console/control-tower" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/benchmarks"
                        element={<Navigate to="/console/benchmarks" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/audit"
                        element={<Navigate to="/console/audit" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/billing"
                        element={<Navigate to="/console/billing" replace />}
                      />
                      <Route
                        path="/dashboard/superadmin/system"
                        element={<Navigate to="/console/system" replace />}
                      />

                      {/* 403 - Access Denied (ProtectedRoute redirect target;
                          must stay un-gated to avoid a redirect loop) */}
                      <Route
                        path="/unauthorized"
                        element={
                          <LazyRoute>
                            <Unauthorized />
                          </LazyRoute>
                        }
                      />

                      {/* 404 - Page Not Found */}
                      <Route
                        path="*"
                        element={
                          <LazyRoute>
                            <NotFound />
                          </LazyRoute>
                        }
                      />
                    </Routes>
                    <Toaster />
                    <OfflineIndicator />
                  </div>
                </UpgradePromptProvider>
              </JoyrideProvider>
            </TooltipProvider>
          </DemoProvider>
        </AuthProvider>
      </ThemeProvider>
    </HelmetProvider>
  );
}

export default App;
