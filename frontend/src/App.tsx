import { Navigate, Route, Routes } from 'react-router-dom';
import { lazy, Suspense } from 'react';
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

// Lazy load pages for code splitting
const Landing = lazy(() => import('./views/Landing'));
const LandingAr = lazy(() => import('./views/LandingAr'));
const Login = lazy(() => import('./views/Login'));
const Signup = lazy(() => import('./views/Signup'));
const ForgotPassword = lazy(() => import('./views/ForgotPassword'));
const ResetPassword = lazy(() => import('./views/ResetPassword'));
const VerifyEmail = lazy(() => import('./views/VerifyEmail'));
const Onboarding = lazy(() => import('./views/Onboarding'));
const UnifiedDashboard = lazy(() => import('./views/dashboard/UnifiedDashboard'));
const CustomDashboard = lazy(() => import('./views/CustomDashboard'));
const Campaigns = lazy(() => import('./views/Campaigns'));
const Stratum = lazy(() => import('./views/Stratum'));
const Benchmarks = lazy(() => import('./views/Benchmarks'));
const Assets = lazy(() => import('./views/Assets'));
const Rules = lazy(() => import('./views/Rules'));
const Competitors = lazy(() => import('./views/Competitors'));
const Predictions = lazy(() => import('./views/Predictions'));
const WhatsApp = lazy(() => import('./views/whatsapp/WhatsAppManager'));
const Settings = lazy(() => import('./views/Settings'));
const Tenants = lazy(() => import('./views/Tenants'));
const MLTraining = lazy(() => import('./views/MLTraining'));
const CAPISetup = lazy(() => import('./views/CAPISetup'));
const SuperadminDashboard = lazy(() => import('./views/SuperadminDashboard'));
const CDPCalculator = lazy(() => import('./views/CDPCalculator'));

// CDP (Customer Data Platform) views
const CDPDashboard = lazy(() => import('./views/cdp/CDPDashboard'));
const CDPProfiles = lazy(() => import('./views/cdp/CDPProfiles'));
const CDPSegments = lazy(() => import('./views/cdp/CDPSegments'));
const CDPEvents = lazy(() => import('./views/cdp/CDPEvents'));
const CDPIdentityGraph = lazy(() => import('./views/cdp/CDPIdentityGraph'));
const CDPAudienceSync = lazy(() => import('./views/cdp/CDPAudienceSync'));
const CDPRfm = lazy(() => import('./views/cdp/CDPRfm'));
const CDPFunnels = lazy(() => import('./views/cdp/CDPFunnels'));
const CDPComputedTraits = lazy(() => import('./views/cdp/CDPComputedTraits'));
const CDPConsent = lazy(() => import('./views/cdp/CDPConsent'));
const CDPPredictiveChurn = lazy(() => import('./views/cdp/CDPPredictiveChurn'));

// Newsletter / Email Campaigns views
const NewsletterDashboard = lazy(() => import('./views/newsletter/NewsletterDashboard'));
const NewsletterCampaigns = lazy(() => import('./views/newsletter/NewsletterCampaigns'));
const NewsletterCampaignEditor = lazy(() => import('./views/newsletter/NewsletterCampaignEditor'));
const NewsletterTemplates = lazy(() => import('./views/newsletter/NewsletterTemplates'));
const NewsletterSubscribers = lazy(() => import('./views/newsletter/NewsletterSubscribers'));
const NewsletterAnalytics = lazy(() => import('./views/newsletter/NewsletterAnalytics'));

// Knowledge Graph views
const KnowledgeGraphInsights = lazy(() => import('./views/KnowledgeGraphInsights'));
const KGProblemDetection = lazy(() => import('./views/knowledge-graph/KGProblemDetection'));
const KGRevenueAttribution = lazy(() => import('./views/knowledge-graph/KGRevenueAttribution'));

// Super Admin views
const ControlTower = lazy(() => import('./views/superadmin/ControlTower'));
const SuperAdminTenantsList = lazy(() => import('./views/superadmin/TenantsList'));
const SuperAdminTenantProfile = lazy(() => import('./views/superadmin/TenantProfile'));
const SuperAdminBenchmarks = lazy(() => import('./views/superadmin/Benchmarks'));
const SuperAdminAudit = lazy(() => import('./views/superadmin/Audit'));
const SuperAdminBilling = lazy(() => import('./views/superadmin/Billing'));
const SuperAdminSystem = lazy(() => import('./views/superadmin/System'));
const SuperAdminCMS = lazy(() => import('./views/superadmin/CMS'));
const SuperAdminUsers = lazy(() => import('./views/superadmin/Users'));

// CMS (Content Management System) - Separate Portal
const CMSLogin = lazy(() => import('./views/CMSLogin'));
const CMSLayout = lazy(() => import('./views/CMSLayout'));
const CMSDashboard = lazy(() => import('./views/cms/CMSDashboard'));
const CMSPosts = lazy(() => import('./views/cms/CMSPosts'));
const CMSPostEditor = lazy(() => import('./views/cms/CMSPostEditor'));
const CMSPages = lazy(() => import('./views/cms/CMSPages'));
const CMSCategories = lazy(() => import('./views/cms/CMSCategories'));
const CMSAuthors = lazy(() => import('./views/cms/CMSAuthors'));
const CMSContacts = lazy(() => import('./views/cms/CMSContacts'));
const CMSLandingFeatures = lazy(() => import('./views/cms/CMSLandingFeatures'));
const CMSLandingFAQ = lazy(() => import('./views/cms/CMSLandingFAQ'));
const CMSLandingPricing = lazy(() => import('./views/cms/CMSLandingPricing'));
const CMSSettingsView = lazy(() => import('./views/cms/CMSSettings'));

// Tenant-scoped views (Campaign Builder)
const ConnectPlatforms = lazy(() => import('./views/tenant/ConnectPlatforms'));
const AdAccounts = lazy(() => import('./views/tenant/AdAccounts'));
const CampaignBuilder = lazy(() => import('./views/tenant/CampaignBuilder'));
const CampaignDrafts = lazy(() => import('./views/tenant/CampaignDrafts'));
const PublishLogs = lazy(() => import('./views/tenant/PublishLogs'));
const TenantOverview = lazy(() => import('./views/tenant/TenantOverview'));
const TenantCampaigns = lazy(() => import('./views/tenant/TenantCampaigns'));
const TenantSettings = lazy(() => import('./views/tenant/TenantSettings'));
const TeamManagement = lazy(() => import('./views/tenant/TeamManagement'));
const TenantInsights = lazy(() => import('./views/tenant/Insights'));
const TenantAuditLog = lazy(() => import('./views/tenant/AuditLog'));

// Role-based tenant views
const TenantAdminOverview = lazy(() => import('./views/tenant/Overview'));
const MediaBuyerConsole = lazy(() => import('./views/tenant/Console'));
const SignalHub = lazy(() => import('./views/tenant/SignalHub'));

// Sprint feature views
const Integrations = lazy(() => import('./views/tenant/Integrations'));
const Pacing = lazy(() => import('./views/tenant/Pacing'));
const ProfitROAS = lazy(() => import('./views/tenant/ProfitROAS'));
const Attribution = lazy(() => import('./views/tenant/Attribution'));
const Reporting = lazy(() => import('./views/tenant/Reporting'));

// P1 Feature views - A/B Testing, DLQ, Model Explainability
const ABTesting = lazy(() => import('./views/tenant/ABTesting'));
const DeadLetterQueue = lazy(() => import('./views/tenant/DeadLetterQueue'));
const ModelExplainability = lazy(() => import('./views/tenant/ModelExplainability'));

// Enterprise feature views
const CustomAutopilotRules = lazy(() => import('./views/CustomAutopilotRules'));
const CustomReportBuilder = lazy(() => import('./views/CustomReportBuilder'));

// Embed Widgets
const EmbedWidgets = lazy(() => import('./views/tenant/EmbedWidgets'));

// Account Manager views
const AMPortfolio = lazy(() => import('./views/am/Portfolio'));
const AMTenantNarrative = lazy(() => import('./views/am/TenantNarrative'));

// Portal views (client VIEWER users)
const PortalLayout = lazy(() => import('./views/portal/PortalLayout'));
const PortalDashboard = lazy(() => import('./views/portal/PortalDashboard'));

// Accept Invite (portal user onboarding)
const AcceptInvite = lazy(() => import('./views/AcceptInvite'));

// Client Assignments (admin UI)
const ClientAssignments = lazy(() => import('./views/tenant/ClientAssignments'));

// Tier-specific landing pages
const TierLandingPage = lazy(() => import('./views/plans/TierLandingPage'));

// Public pages (Product)
const FeaturesPage = lazy(() => import('./views/pages/Features'));
const PricingPage = lazy(() => import('./views/pages/Pricing'));
const IntegrationsPage = lazy(() => import('./views/pages/Integrations'));
const ApiDocsPage = lazy(() => import('./views/pages/ApiDocs'));

// Public pages (Solutions)
const CDPSolutionPage = lazy(() => import('./views/pages/solutions/CDP'));
const AudienceSyncPage = lazy(() => import('./views/pages/solutions/AudienceSync'));
const PredictionsSolutionPage = lazy(() => import('./views/pages/solutions/PredictionsSolution'));
const TrustEnginePage = lazy(() => import('./views/pages/solutions/TrustEngine'));

// Public pages (Company)
const AboutPage = lazy(() => import('./views/pages/company/About'));
const CareersPage = lazy(() => import('./views/pages/company/Careers'));
const BlogPage = lazy(() => import('./views/pages/company/Blog'));
const BlogPostPage = lazy(() => import('./views/pages/company/BlogPost'));
const ContactPage = lazy(() => import('./views/pages/company/Contact'));
const FAQPage = lazy(() => import('./views/pages/company/FAQ'));

// Public pages (Legal)
const PrivacyPage = lazy(() => import('./views/pages/legal/Privacy'));
const TermsPage = lazy(() => import('./views/pages/legal/Terms'));
const SecurityPage = lazy(() => import('./views/pages/legal/Security'));
const DPAPage = lazy(() => import('./views/pages/legal/DPA'));

// Public pages (Resources)
const DocsPage = lazy(() => import('./views/pages/resources/Docs'));
const ChangelogPage = lazy(() => import('./views/pages/resources/Changelog'));
const CaseStudiesPage = lazy(() => import('./views/pages/resources/CaseStudies'));
const ResourcesPage = lazy(() => import('./views/pages/resources/Resources'));
const StatusPage = lazy(() => import('./views/pages/resources/Status'));
const ComparisonPage = lazy(() => import('./views/pages/resources/Comparison'));
const GlossaryPage = lazy(() => import('./views/pages/resources/Glossary'));
const NotFound = lazy(() => import('./views/NotFound'));

// Announcement pages
const AudienceSyncLaunch = lazy(() => import('./views/pages/announcements/AudienceSyncLaunch'));

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

                    {/* CMS Portal (protected - admin/superadmin only) */}
                    <Route
                      path="/cms"
                      element={
                        <ProtectedRoute requiredRole="admin">
                          <Suspense fallback={<LoadingSpinner />}>
                            <CMSLayout />
                          </Suspense>
                        </ProtectedRoute>
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
                        <Suspense fallback={<LoadingSpinner />}>
                          <PrivacyPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/terms"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <TermsPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/security"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <SecurityPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/dpa"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <DPAPage />
                        </Suspense>
                      }
                    />

                    {/* Resources pages (public) */}
                    <Route
                      path="/docs"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <DocsPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/changelog"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <ChangelogPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/case-studies"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <CaseStudiesPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/resources"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <ResourcesPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/status"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <StatusPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/compare"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <ComparisonPage />
                        </Suspense>
                      }
                    />
                    <Route
                      path="/glossary"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <GlossaryPage />
                        </Suspense>
                      }
                    />

                    {/* Announcement pages */}
                    <Route
                      path="/announcements/audience-sync"
                      element={
                        <Suspense fallback={<LoadingSpinner />}>
                          <AudienceSyncLaunch />
                        </Suspense>
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

                    {/* Protected dashboard routes - wrapped with onboarding guard */}
                    <Route
                      path="/dashboard"
                      element={
                        <ProtectedRoute>
                          <OnboardingGuard>
                            <DashboardLayout />
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
                          <Suspense fallback={<LoadingSpinner />}>
                            <Settings />
                          </Suspense>
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

                      {/* Enterprise feature routes */}
                      <Route
                        path="custom-autopilot-rules"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CustomAutopilotRules />
                          </Suspense>
                        }
                      />
                      <Route
                        path="custom-reports"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <CustomReportBuilder />
                          </Suspense>
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
                        path="superadmin/cms"
                        element={
                          <ProtectedRoute requiredRole="superadmin">
                            <Suspense fallback={<LoadingSpinner />}>
                              <SuperAdminCMS />
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

                    {/* Tenant-scoped routes with :tenantId parameter - wrapped with onboarding guard */}
                    <Route
                      path="/app/:tenantId"
                      element={
                        <ProtectedRoute>
                          <OnboardingGuard>
                            <TenantLayout />
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

                      {/* Tenant Settings */}
                      <Route
                        path="settings"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantSettings />
                          </Suspense>
                        }
                      />

                      {/* Team Management */}
                      <Route
                        path="team"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TeamManagement />
                          </Suspense>
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

                      {/* Tenant Insights */}
                      <Route
                        path="insights"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantInsights />
                          </Suspense>
                        }
                      />

                      {/* Tenant Audit Log */}
                      <Route
                        path="audit-log"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <TenantAuditLog />
                          </Suspense>
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

                      {/* Reporting */}
                      <Route
                        path="reporting"
                        element={
                          <Suspense fallback={<LoadingSpinner />}>
                            <Reporting />
                          </Suspense>
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
