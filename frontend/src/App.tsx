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

// Lazy load pages for code splitting
const Login = lazy(() => import('./views/Login'))
const Overview = lazy(() => import('./views/Overview'))
const CustomDashboard = lazy(() => import('./views/CustomDashboard'))
const Campaigns = lazy(() => import('./views/Campaigns'))
const Stratum = lazy(() => import('./views/Stratum'))
const Benchmarks = lazy(() => import('./views/Benchmarks'))
const Assets = lazy(() => import('./views/Assets'))
const Rules = lazy(() => import('./views/Rules'))
const WhatsApp = lazy(() => import('./views/WhatsApp'))
const Settings = lazy(() => import('./views/Settings'))
const Tenants = lazy(() => import('./views/Tenants'))
const MLTraining = lazy(() => import('./views/MLTraining'))
const CAPISetup = lazy(() => import('./views/CAPISetup'))
const DataQuality = lazy(() => import('./views/DataQuality'))
const DataQualityDashboard = lazy(() => import('./views/DataQualityDashboard'))
const SuperadminDashboard = lazy(() => import('./views/SuperadminDashboard'))

// Tenant-scoped views (Campaign Builder)
const ConnectPlatforms = lazy(() => import('./views/tenant/ConnectPlatforms'))
const AdAccounts = lazy(() => import('./views/tenant/AdAccounts'))
const CampaignBuilder = lazy(() => import('./views/tenant/CampaignBuilder'))
const CampaignDrafts = lazy(() => import('./views/tenant/CampaignDrafts'))
const PublishLogs = lazy(() => import('./views/tenant/PublishLogs'))
const TenantOverview = lazy(() => import('./views/tenant/TenantOverview'))
const TenantCampaigns = lazy(() => import('./views/tenant/TenantCampaigns'))
const TenantSettings = lazy(() => import('./views/tenant/TenantSettings'))

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <JoyrideProvider>
          <div className="min-h-screen bg-background">
            <Routes>
              {/* Public routes */}
              <Route
                path="/login"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <Login />
                  </Suspense>
                }
              />

              {/* Protected routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/overview" replace />} />
                <Route
                  path="overview"
                  element={
                    <Suspense fallback={<LoadingSpinner />}>
                      <Overview />
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
              </Route>

              {/* Tenant-scoped routes with :tenantId parameter */}
              <Route
                path="/app/:tenantId"
                element={
                  <ProtectedRoute>
                    <TenantLayout />
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
              </Route>

              {/* Catch all - redirect to overview */}
              <Route path="*" element={<Navigate to="/overview" replace />} />
            </Routes>
            <Toaster />
          </div>
        </JoyrideProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
