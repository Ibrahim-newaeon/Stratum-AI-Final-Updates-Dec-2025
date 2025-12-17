import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import DashboardLayout from './views/DashboardLayout'
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
