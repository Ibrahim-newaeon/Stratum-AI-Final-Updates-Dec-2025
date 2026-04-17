import { Navigate, Route, Routes } from 'react-router-dom';
import { ComponentType, lazy, Suspense } from 'react';
import { HelmetProvider } from 'react-helmet-async';
import DashboardLayout from './views/DashboardLayout';
import TenantLayout from './views/TenantLayout';
import { Toaster } from './components/ui/toaster';
import { TooltipProvider } from './components/ui/tooltip';
import { JoyrideProvider } from './components/guide/JoyrideWrapper';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { DemoProvider } from './contexts/DemoContext';
import LoadingSpinner from './components/common/LoadingSpinner';
import ProtectedRoute from './components/auth/ProtectedRoute';
import CMSProtectedRoute from './components/auth/CMSProtectedRoute';
import OnboardingGuard from './components/auth/OnboardingGuard';
import { SkipToContent } from './components/ui/skip-to-content';
import { useDocumentDirection } from './hooks/useDocumentDirection';
import { OfflineIndicator } from './components/common/OfflineIndicator';
import { ErrorBoundary } from './components/ui/ErrorBoundary';

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
const UnifiedDashboard = lazyWithRetry(() => import('./views/dashboard/UnifiedDashboard'));
const CustomDashboard = lazyWithRetry(() => import('./views/CustomDashboard'));
const Campaigns = lazyWithRetry(() => import('./views/Campaigns'));
const CampaignDetail = lazyWithRetry(() => import('./views/CampaignDetail'));
const Stratum = lazyWithRetry(() => import('./views/Stratum'));
const Benchmarks = lazyWithRetry(() => import('./views/Benchmarks'));
const Assets = lazyWithRetry(() => import('./views/Assets'));
const Rules = lazyWithRetry(() => import('./views/Rules'));
const Competitors = lazyWithRetry(() => import('./views/Competitors'));
const Predictions = lazyWithRetry(() => import('./views/Predictions'));
const WhatsApp = lazyWithRetry(() => import('./views/whatsapp/WhatsAppManager'));
const Settings = lazyWithRetry(() => import('./views/Settings'));
const Tenants = lazyWithRetry(() => import('./views/Tenants'));
const MLTraining = lazyWithRetry(() => import('./views/MLTraining'));
const CAPISetup = lazyWithRetry(() => import('./views/CAPISetup'));
const SuperadminDashboard = lazyWithRetry(() => import('./views/SuperadminDashboard'));
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

// Newsletter / Email Campaigns views
const NewsletterDashboard = lazyWithRetry(() => import('./views/newsletter/NewsletterDashboard'));
const NewsletterCampaigns = lazyWithRetry(() => import('./views/newsletter/NewsletterCampaigns'));
const NewsletterCampaignEditor = lazyWithRetry(() => import('./views/newsletter/NewsletterCampaignEditor'));
const NewsletterTemplates = lazyWithRetry(() => import('./views/newsletter/NewsletterTemplates'));
const NewsletterSubscribers = lazyWithRetry(() => import('./views/newsletter/NewsletterSubscribers'));
const NewsletterAnalytics = lazyWithRetry(() => import('./views/newsletter/NewsletterAnalytics'));

// Knowledge Graph views
const KnowledgeGraphInsights = lazyWithRetry(() => import('./views/KnowledgeGraphInsights'));
const KGProblemDetection = lazyWithRetry(() => import('./views/knowledge-graph/KGProblemDetection'));
const KGRevenueAttribution = lazyWithRetry(() => import('./views/knowledge-graph/KGRevenueAttribution'));

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
const Integrations = lazyWithRetry(() => import('./views/tenant/Integrations'));
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
const PredictionsSolutionPage = lazyWithRetry(() => import('./views/pages/solutions/PredictionsSolution'));
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
const ChangelogPage = lazyWithRetry(() => import('./views/pages/resources/Changelog'));
const CaseStudiesPage = lazyWithRetry(() => import('./views/pages/resources/CaseStudies'));
const ResourcesPage = lazyWithRetry(() => import('./views/pages/resources/Resources'));
const StatusPage = lazyWithRetry(() => import('./views/pages/resources/Status'));
const ComparisonPage = lazyWithRetry(() => import('./views/pages/resources/Comparison'));
const GlossaryPage = lazyWithRetry(() => import('./views/pages/resources/Glossary'));
const NotFound = lazyWithRetry(() => import('./views/NotFound'));

// Checkout flow
const CheckoutPage = lazyWithRetry(() => import('./views/checkout/CheckoutPage'));
const CheckoutSuccess = lazyWithRetry(() => import('./views/checkout/CheckoutSuccess'));
const CheckoutCancel = lazyWithRetry(() => import('./views/checkout/CheckoutCancel'));

// Announcement pages
const AudienceSyncLaunch = lazyWithRetry(() => import('./views/pages/announcements/AudienceSyncLaunch'));

function App() {
  return (
    <HelmetProvider>
      <ThemeProvider>
        <AuthProvider>
          <DemoProvider>
            <TooltipProvider delayDuration={300}>
              <JoyrideProvider>
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
                          <Suspense fallback={<LoadingSpinner />}>
                            <Landing />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/ar"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <LandingAr />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/login"
                      element={
                        <ErrorBoundary message="Failed to load the login page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <Login />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/signup"
                      element={
                        <ErrorBoundary message="Failed to load the signup page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <Signup />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/forgot-password"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <ForgotPassword />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/reset-password"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <ResetPassword />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/verify-email"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <VerifyEmail />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />

                    {/* Accept Invite (public - portal user onboarding) */}
                    <Route
                      path="/accept-invite"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <AcceptInvite />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />

                    {/* CMS Login (public) */}
                    <Route
                      path="/cms-login"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <CMSLogin />
                        </Suspense>
                      }
                    />

                    {/* CMS Portal (protected - requires cms_role) */}
                    <Route
                      path="/cms"
                      element={
                        <CMSProtectedRoute>
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSLayout />
                          </Suspense>
                        </CMSProtectedRoute>
                      }
                    >
                      <Route
                        index
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSDashboard />
                          </Suspense>
                        }
                      />
                      {/* Posts Management */}
                      <Route
                        path="posts"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSPosts />
                          </Suspense>
                        }
                      />
                      {/* Post Create */}
                      <Route
                        path="posts/new"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSPostEditor />
                          </Suspense>
                        }
                      />
                      {/* Post Edit */}
                      <Route
                        path="posts/:id"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSPostEditor />
                          </Suspense>
                        }
                      />
                      {/* Categories Management */}
                      <Route
                        path="categories"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSCategories />
                          </Suspense>
                        }
                      />
                      {/* Authors Management */}
                      <Route
                        path="authors"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSAuthors />
                          </Suspense>
                        }
                      />
                      {/* Contact Submissions */}
                      <Route
                        path="contacts"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSContacts />
                          </Suspense>
                        }
                      />
                      {/* Pages Management */}
                      <Route
                        path="pages"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSPages />
                          </Suspense>
                        }
                      />
                      {/* Landing Content - Features */}
                      <Route
                        path="landing/features"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSLandingFeatures />
                          </Suspense>
                        }
                      />
                      {/* Landing Content - FAQ */}
                      <Route
                        path="landing/faq"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSLandingFAQ />
                          </Suspense>
                        }
                      />
                      {/* Landing Content - Pricing */}
                      <Route
                        path="landing/pricing"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSLandingPricing />
                          </Suspense>
                        }
                      />
                      {/* CMS Settings */}
                      <Route
                        path="settings"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSSettingsView />
                          </Suspense>
                        }
                      />
                      {/* CMS User Management */}
                      <Route
                        path="users"
                        element={
                          <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400" /></div>}>
                            <CMSUsers />
                          </Suspense>
                        }
                      />
                    </Route>

                    {/* CDP ROI Calculator (public) */}
                    <Route
                      path="/cdp-calculator"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <CDPCalculator />
                        </Suspense>
                      }
                    />

                    {/* Tier-specific landing pages (public) */}
                    <Route
                      path="/plans/:tier"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <TierLandingPage />
                        </Suspense>
                      }
                    />

                    {/* Product pages (public) */}
                    <Route
                      path="/features"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <FeaturesPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/pricing"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <PricingPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/integrations"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <IntegrationsPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/api-docs"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <ApiDocsPage />
                        </Suspense>
                      }
                    />

                    {/* Solutions pages (public) */}
                    <Route
                      path="/solutions/cdp"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <CDPSolutionPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/solutions/audience-sync"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <AudienceSyncPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/solutions/predictions"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <PredictionsSolutionPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/solutions/trust-engine"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <TrustEnginePage />
                        </Suspense>
                      }
                    />

                    {/* Company pages (public) */}
                    <Route
                      path="/about"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <AboutPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/careers"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <CareersPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/blog"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <BlogPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/blog/:slug"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <BlogPostPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/contact"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <ContactPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/faq"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <FAQPage />
                        </Suspense>
                      }
                    />

                    {/* Legal pages (public) */}
                    <Route
                      path="/privacy"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <PrivacyPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/terms"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <TermsPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/security"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <SecurityPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/dpa"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <DPAPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />

                    {/* Resources pages (public) */}
                    <Route
                      path="/docs"
                      element={
                        <ErrorBoundary message="Failed to load the documentation page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <DocsPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/changelog"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <ChangelogPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/case-studies"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <CaseStudiesPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/resources"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <ResourcesPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/status"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <StatusPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/compare"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <ComparisonPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />
                    <Route
                      path="/glossary"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <GlossaryPage />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />

                    {/* Announcement pages */}
                    <Route
                      path="/announcements/audience-sync"
                      element={
                        <ErrorBoundary message="Failed to load the page">
                          <Suspense fallback={<LoadingSpinner />}>
                            <AudienceSyncLaunch />
                          </Suspense>
                        </ErrorBoundary>
                      }
                    />

                    {/* Client Portal routes (portal/VIEWER users only) */}
                    <Route
                      path="/portal"
                      element={
                        <ProtectedRoute portalOnly>
                          <Suspense fallback={<LoadingSpinner />}>
                            <PortalLayout />
                          </Suspense>
                        </ProtectedRoute>
                      }
                    >
                      <Route
                        index
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <PortalDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <PortalDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="requests"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <PortalDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="profile"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Settings />
                          </Suspense>
                        }
                      />
                    </Route>

                    {/* Onboarding wizard (protected) */}
                    <Route
                      path="/onboarding"
                      element={
                        <ProtectedRoute>
                          <Suspense fallback={<LoadingSpinner />}>
                            <Onboarding />
                          </Suspense>
                        </ProtectedRoute>
                      }
                    />

                    {/* Checkout flow (protected) */}
                    <Route
                      path="/checkout"
                      element={
                        <ProtectedRoute>
                          <Suspense fallback={<LoadingSpinner />}>
                            <CheckoutPage />
                          </Suspense>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/checkout/success"
                      element={
                        <ProtectedRoute>
                          <Suspense fallback={<LoadingSpinner />}>
                            <CheckoutSuccess />
                          </Suspense>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/checkout/cancel"
                      element={
                        <ProtectedRoute>
                          <Suspense fallback={<LoadingSpinner />}>
                            <CheckoutCancel />
                          </Suspense>
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
                      <Route
                        path="overview"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <UnifiedDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="custom-dashboard"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CustomDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Campaigns />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns/:id"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CampaignDetail />
                          </Suspense>
                        }
                      />
                      <Route
                        path="stratum"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Stratum />
                          </Suspense>
                        }
                      />
                      <Route
                        path="benchmarks"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Benchmarks />
                          </Suspense>
                        }
                      />
                      <Route
                        path="assets"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Assets />
                          </Suspense>
                        }
                      />
                      <Route
                        path="rules"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Rules />
                          </Suspense>
                        }
                      />
                      <Route
                        path="competitors"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Competitors />
                          </Suspense>
                        }
                      />
                      <Route
                        path="predictions"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Predictions />
                          </Suspense>
                        }
                      />
                      <Route
                        path="whatsapp"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <WhatsApp />
                          </Suspense>
                        }
                      />
                      <Route
                        path="settings"
                        element={
                          <ProtectedRoute requiredRole="admin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <Settings />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="tenants"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Tenants />
                          </Suspense>
                        }
                      />
                      <Route
                        path="ml-training"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <MLTraining />
                          </Suspense>
                        }
                      />
                      <Route
                        path="integrations"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CAPISetup />
                          </Suspense>
                        }
                      />

                      {/* Signal Hub (EMQ / Signal Health) */}
                      <Route
                        path="signal-hub"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <SignalHub />
                          </Suspense>
                        }
                      />

                      {/* CDP (Customer Data Platform) routes */}
                      <Route
                        path="cdp"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/profiles"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPProfiles />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/segments"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPSegments />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/events"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPEvents />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/identity"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPIdentityGraph />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/audience-sync"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPAudienceSync />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/rfm"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPRfm />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/funnels"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPFunnels />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/computed-traits"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPComputedTraits />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/consent"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPConsent />
                          </Suspense>
                        }
                      />
                      <Route
                        path="cdp/predictive-churn"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CDPPredictiveChurn />
                          </Suspense>
                        }
                      />

                      {/* Newsletter / Email Campaign routes */}
                      <Route
                        path="newsletter"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterDashboard />
                          </Suspense>
                        }
                      />
                      <Route
                        path="newsletter/campaigns"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterCampaigns />
                          </Suspense>
                        }
                      />
                      <Route
                        path="newsletter/campaigns/new"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterCampaignEditor />
                          </Suspense>
                        }
                      />
                      <Route
                        path="newsletter/campaigns/:id/edit"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterCampaignEditor />
                          </Suspense>
                        }
                      />
                      <Route
                        path="newsletter/campaigns/:id/analytics"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterAnalytics />
                          </Suspense>
                        }
                      />
                      <Route
                        path="newsletter/templates"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterTemplates />
                          </Suspense>
                        }
                      />
                      <Route
                        path="newsletter/subscribers"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <NewsletterSubscribers />
                          </Suspense>
                        }
                      />

                      {/* Knowledge Graph routes */}
                      <Route
                        path="knowledge-graph"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <KnowledgeGraphInsights />
                          </Suspense>
                        }
                      />
                      <Route
                        path="knowledge-graph/insights"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <KnowledgeGraphInsights />
                          </Suspense>
                        }
                      />
                      <Route
                        path="knowledge-graph/problems"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <KGProblemDetection />
                          </Suspense>
                        }
                      />
                      <Route
                        path="knowledge-graph/revenue"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <KGRevenueAttribution />
                          </Suspense>
                        }
                      />

                      {/* Enterprise feature routes (admin+ only) */}
                      <Route
                        path="custom-autopilot-rules"
                        element={
                          <ProtectedRoute requiredRole="admin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <CustomAutopilotRules />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="custom-reports"
                        element={
                          <ProtectedRoute requiredRole="manager">
                            <Suspense fallback={<LoadingSpinner />}>
                              <CustomReportBuilder />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Superadmin only routes */}
                      <Route
                        path="superadmin"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperadminDashboard />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/control-tower"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <ControlTower />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/tenants"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminTenantsList />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/tenants/:tenantId"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminTenantProfile />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/benchmarks"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminBenchmarks />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/audit"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminAudit />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/billing"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminBilling />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/system"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminSystem />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="superadmin/users"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminUsers />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Account Manager routes */}
                      <Route
                        path="am/portfolio"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <AMPortfolio />
                          </Suspense>
                        }
                      />
                      <Route
                        path="am/tenant/:tenantId"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <AMTenantNarrative />
                          </Suspense>
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
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantOverview />
                          </Suspense>
                        }
                      />
                      <Route
                        path="overview"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantOverview />
                          </Suspense>
                        }
                      />

                      {/* Role-based views */}
                      <Route
                        path="trust"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantAdminOverview />
                          </Suspense>
                        }
                      />
                      <Route
                        path="console"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <MediaBuyerConsole />
                          </Suspense>
                        }
                      />
                      <Route
                        path="signal-hub"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <SignalHub />
                          </Suspense>
                        }
                      />

                      {/* Campaigns Management */}
                      <Route
                        path="campaigns"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantCampaigns />
                          </Suspense>
                        }
                      />

                      {/* Campaign Builder Routes */}
                      <Route
                        path="campaigns/connect"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <ConnectPlatforms />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns/accounts"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <AdAccounts />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns/new"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CampaignBuilder />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns/drafts"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CampaignDrafts />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns/drafts/:draftId"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CampaignBuilder />
                          </Suspense>
                        }
                      />
                      <Route
                        path="campaigns/logs"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <PublishLogs />
                          </Suspense>
                        }
                      />

                      {/* Tenant Settings (admin+ only) */}
                      <Route
                        path="settings"
                        element={
                          <ProtectedRoute requiredRole="admin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <TenantSettings />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Team Management (admin+ only) */}
                      <Route
                        path="team"
                        element={
                          <ProtectedRoute requiredRole="admin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <TeamManagement />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Client Assignments (admin+ only) */}
                      <Route
                        path="client-assignments"
                        element={
                          <ProtectedRoute requiredRole="admin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <ClientAssignments />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Tenant Insights (manager+ only) */}
                      <Route
                        path="insights"
                        element={
                          <ProtectedRoute requiredRole="manager">
                            <Suspense fallback={<LoadingSpinner />}>
                              <TenantInsights />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Tenant Audit Log (admin+ only) */}
                      <Route
                        path="audit-log"
                        element={
                          <ProtectedRoute requiredRole="admin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <TenantAuditLog />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* Competitors */}
                      <Route
                        path="competitors"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Competitors />
                          </Suspense>
                        }
                      />

                      {/* Benchmarks */}
                      <Route
                        path="benchmarks"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Benchmarks />
                          </Suspense>
                        }
                      />

                      {/* Assets */}
                      <Route
                        path="assets"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Assets />
                          </Suspense>
                        }
                      />

                      {/* Rules */}
                      <Route
                        path="rules"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Rules />
                          </Suspense>
                        }
                      />

                      {/* Predictions */}
                      <Route
                        path="predictions"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Predictions />
                          </Suspense>
                        }
                      />

                      {/* Sprint Feature Routes */}
                      {/* CRM Integrations */}
                      <Route
                        path="integrations"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Integrations />
                          </Suspense>
                        }
                      />

                      {/* Pacing & Forecasting */}
                      <Route
                        path="pacing"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Pacing />
                          </Suspense>
                        }
                      />

                      {/* Profit ROAS */}
                      <Route
                        path="profit"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <ProfitROAS />
                          </Suspense>
                        }
                      />

                      {/* Attribution */}
                      <Route
                        path="attribution"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Attribution />
                          </Suspense>
                        }
                      />

                      {/* Reporting (manager+ only) */}
                      <Route
                        path="reporting"
                        element={
                          <ProtectedRoute requiredRole="manager">
                            <Suspense fallback={<LoadingSpinner />}>
                              <Reporting />
                            </Suspense>
                          </ProtectedRoute>
                        }
                      />

                      {/* A/B Testing */}
                      <Route
                        path="ab-testing"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <ABTesting />
                          </Suspense>
                        }
                      />

                      {/* Dead Letter Queue (CAPI) */}
                      <Route
                        path="dead-letter-queue"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <DeadLetterQueue />
                          </Suspense>
                        }
                      />

                      {/* Model Explainability (SHAP/LIME/LTV) */}
                      <Route
                        path="explainability"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <ModelExplainability />
                          </Suspense>
                        }
                      />

                      {/* Embed Widgets */}
                      <Route
                        path="embed-widgets"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <EmbedWidgets />
                          </Suspense>
                        }
                      />
                    </Route>

                    {/* Legacy route redirects */}
                    <Route
                      path="/overview"
                      element={<Navigate to="/dashboard/overview" replace />}
                    />

                    {/* 404 - Page Not Found */}
                    <Route
                      path="*"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <NotFound />
                        </Suspense>
                      }
                    />
                  </Routes>
                  <Toaster />
                  <OfflineIndicator />
                </div>
              </JoyrideProvider>
            </TooltipProvider>
          </DemoProvider>
        </AuthProvider>
      </ThemeProvider>
    </HelmetProvider>
  );
}

export default App;
