import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import DashboardLayout from './views/DashboardLayout'
import TenantLayout from './views/TenantLayout'
import { Toaster } from './components/ui/toaster'
import { JoyrideProvider } from './components/guide/JoyrideWrapper'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import LoadingSpinner from './components/common/LoadingSpinner'
import ProtectedRoute from './components/auth/ProtectedRoute'
import OnboardingGuard from './components/auth/OnboardingGuard'

// Lazy load pages for code splitting
const Landing = lazy(() => import('./views/Landing'))
const LandingAr = lazy(() => import('./views/LandingAr'))
const Login = lazy(() => import('./views/Login'))
const Signup = lazy(() => import('./views/Signup'))
const ForgotPassword = lazy(() => import('./views/ForgotPassword'))
const ResetPassword = lazy(() => import('./views/ResetPassword'))
const VerifyEmail = lazy(() => import('./views/VerifyEmail'))
const Onboarding = lazy(() => import('./views/Onboarding'))
const UnifiedDashboard = lazy(() => import('./views/dashboard/UnifiedDashboard'))
const CustomDashboard = lazy(() => import('./views/CustomDashboard'))
const Campaigns = lazy(() => import('./views/Campaigns'))
const Stratum = lazy(() => import('./views/Stratum'))
const Benchmarks = lazy(() => import('./views/Benchmarks'))
const Assets = lazy(() => import('./views/Assets'))
const Rules = lazy(() => import('./views/Rules'))
const Competitors = lazy(() => import('./views/Competitors'))
const Predictions = lazy(() => import('./views/Predictions'))
const WhatsApp = lazy(() => import('./views/WhatsApp'))
const Settings = lazy(() => import('./views/Settings'))
const Tenants = lazy(() => import('./views/Tenants'))
const MLTraining = lazy(() => import('./views/MLTraining'))
const CAPISetup = lazy(() => import('./views/CAPISetup'))
const DataQuality = lazy(() => import('./views/DataQuality'))
const DataQualityDashboard = lazy(() => import('./views/DataQualityDashboard'))
const SuperadminDashboard = lazy(() => import('./views/SuperadminDashboard'))
const CDPCalculator = lazy(() => import('./views/CDPCalculator'))

// CDP (Customer Data Platform) views
const CDPDashboard = lazy(() => import('./views/cdp/CDPDashboard'))
const CDPProfiles = lazy(() => import('./views/cdp/CDPProfiles'))
const CDPSegments = lazy(() => import('./views/cdp/CDPSegments'))
const CDPEvents = lazy(() => import('./views/cdp/CDPEvents'))
const CDPIdentityGraph = lazy(() => import('./views/cdp/CDPIdentityGraph'))
const CDPAudienceSync = lazy(() => import('./views/cdp/CDPAudienceSync'))
const CDPRfm = lazy(() => import('./views/cdp/CDPRfm'))
const CDPFunnels = lazy(() => import('./views/cdp/CDPFunnels'))
const CDPComputedTraits = lazy(() => import('./views/cdp/CDPComputedTraits'))
const CDPConsent = lazy(() => import('./views/cdp/CDPConsent'))
const CDPPredictiveChurn = lazy(() => import('./views/cdp/CDPPredictiveChurn'))

// Super Admin views
const ControlTower = lazy(() => import('./views/superadmin/ControlTower'))
const SuperAdminTenantsList = lazy(() => import('./views/superadmin/TenantsList'))
const SuperAdminTenantProfile = lazy(() => import('./views/superadmin/TenantProfile'))
const SuperAdminBenchmarks = lazy(() => import('./views/superadmin/Benchmarks'))
const SuperAdminAudit = lazy(() => import('./views/superadmin/Audit'))
const SuperAdminBilling = lazy(() => import('./views/superadmin/Billing'))
const SuperAdminSystem = lazy(() => import('./views/superadmin/System'))

// Tenant-scoped views (Campaign Builder)
const ConnectPlatforms = lazy(() => import('./views/tenant/ConnectPlatforms'))
const AdAccounts = lazy(() => import('./views/tenant/AdAccounts'))
const CampaignBuilder = lazy(() => import('./views/tenant/CampaignBuilder'))
const CampaignDrafts = lazy(() => import('./views/tenant/CampaignDrafts'))
const PublishLogs = lazy(() => import('./views/tenant/PublishLogs'))
const TenantOverview = lazy(() => import('./views/tenant/TenantOverview'))
const TenantCampaigns = lazy(() => import('./views/tenant/TenantCampaigns'))
const TenantSettings = lazy(() => import('./views/tenant/TenantSettings'))
const TeamManagement = lazy(() => import('./views/tenant/TeamManagement'))

// Role-based tenant views
const TenantAdminOverview = lazy(() => import('./views/tenant/Overview'))
const MediaBuyerConsole = lazy(() => import('./views/tenant/Console'))
const SignalHub = lazy(() => import('./views/tenant/SignalHub'))

// Sprint feature views
const Integrations = lazy(() => import('./views/tenant/Integrations'))
const Pacing = lazy(() => import('./views/tenant/Pacing'))
const ProfitROAS = lazy(() => import('./views/tenant/ProfitROAS'))
const Attribution = lazy(() => import('./views/tenant/Attribution'))
const Reporting = lazy(() => import('./views/tenant/Reporting'))

// P1 Feature views - A/B Testing, DLQ, Model Explainability
const ABTesting = lazy(() => import('./views/tenant/ABTesting'))
const DeadLetterQueue = lazy(() => import('./views/tenant/DeadLetterQueue'))
const ModelExplainability = lazy(() => import('./views/tenant/ModelExplainability'))

// Enterprise feature views
const CustomAutopilotRules = lazy(() => import('./views/CustomAutopilotRules'))
const CustomReportBuilder = lazy(() => import('./views/CustomReportBuilder'))

// Embed Widgets
const EmbedWidgets = lazy(() => import('./views/tenant/EmbedWidgets'))

// Account Manager views
const AMPortfolio = lazy(() => import('./views/am/Portfolio'))
const AMTenantNarrative = lazy(() => import('./views/am/TenantNarrative'))

// Tier-specific landing pages
const TierLandingPage = lazy(() => import('./views/plans/TierLandingPage'))

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <JoyrideProvider>
          <div className="min-h-screen bg-background">
            <Routes>
              {/* Public routes */}
              <Route
                path="/"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Landing />
                  </Suspense>
                }
              />
              <Route
                path="/ar"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <LandingAr />
                  </Suspense>
                }
              />
              <Route
                path="/login"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Login />
                  </Suspense>
                }
              />
              <Route
                path="/signup"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Signup />
                  </Suspense>
                }
              />
              <Route
                path="/forgot-password"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <ForgotPassword />
                  </Suspense>
                }
              />
              <Route
                path="/reset-password"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <ResetPassword />
                  </Suspense>
                }
              />
              <Route
                path="/verify-email"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <VerifyEmail />
                  </Suspense>
                }
              />

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
              path="dashboard"
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
              path="capi-setup"
              element={
                <Suspense fallback={<LoadingSpinner />}>
                  <CAPISetup />
                </Suspense>
              }
            />
            <Route
              path="data-quality"
              element={
                <Suspense fallback={<LoadingSpinner />}>
                  <DataQuality />
                </Suspense>
              }
            />
                <Route
                  path="emq-dashboard"
                  element={
                    <Suspense fallback={<LoadingSpinner />}>
                      <DataQualityDashboard />
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
              <Route path="/overview" element={<Navigate to="/dashboard/overview" replace />} />

              {/* Catch all - redirect to landing for unauthenticated, dashboard for authenticated */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            <Toaster />
          </div>
        </JoyrideProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
