/**
 * Login Page
 * Authentication entry point for Stratum AI
 * Theme: Infobip-inspired dark design matching landing.html
 */

import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import {
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  // Get the redirect path from location state
  const from = (location.state as any)?.from?.pathname || '/dashboard/overview'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const result = await login(email, password)

      if (result.success) {
        navigate(from, { replace: true })
      } else {
        setError(result.error || 'Login failed')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDemoLogin = async (role: 'superadmin' | 'admin' | 'user') => {
    const credentials = {
      superadmin: { email: 'superadmin@stratum.ai', password: 'Admin123!' },
      admin: { email: 'demo@stratum.ai', password: 'demo1234' },
      user: { email: 'demo@stratum.ai', password: 'demo1234' },
    }

    const { email, password } = credentials[role]
    setEmail(email)
    setPassword(password)
    setError('')
    setIsLoading(true)

    try {
      const result = await login(email, password)
      if (result.success) {
        navigate(from, { replace: true })
      } else {
        setError(result.error || 'Login failed')
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#030303' }}>
      {/* Animated Background Orbs - 2026 Theme */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute w-[600px] h-[600px] rounded-full blur-[80px] opacity-40 animate-[orbFloat_15s_ease-in-out_infinite]"
          style={{
            background: 'rgba(168, 85, 247, 0.25)',
            top: '-200px',
            left: '-200px'
          }}
        />
        <div
          className="absolute w-[500px] h-[500px] rounded-full blur-[80px] opacity-40 animate-[orbFloat_15s_ease-in-out_infinite]"
          style={{
            background: 'rgba(6, 182, 212, 0.25)',
            bottom: '-150px',
            right: '-150px',
            animationDelay: '-5s'
          }}
        />
        <div
          className="absolute w-[400px] h-[400px] rounded-full blur-[80px] opacity-30 animate-[orbFloat_15s_ease-in-out_infinite]"
          style={{
            background: 'rgba(249, 115, 22, 0.18)',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            animationDelay: '-10s'
          }}
        />
      </div>

      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)' }} />

        <div className="relative z-10 flex flex-col justify-between p-12 text-white w-full">
          <div>
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 mb-12">
              <div
                className="h-12 w-12 rounded-xl flex items-center justify-center"
                style={{ background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)' }}
              >
                <span className="text-white font-bold text-2xl">S</span>
              </div>
              <span
                className="text-3xl font-bold"
                style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}
              >
                Stratum AI
              </span>
            </Link>

            <h1 className="text-4xl font-bold mb-4 leading-tight" style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
              Revenue Operating System
              <br />
              <span style={{ color: '#f97316' }}>with Trust-Gated Autopilot</span>
            </h1>
            <p className="text-lg max-w-md" style={{ color: 'rgba(255, 255, 255, 0.75)' }}>
              AI-powered marketing intelligence with real-time attribution, signal health monitoring, and automated optimization across all ad platforms.
            </p>
          </div>

          {/* Platform logos */}
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              {/* Meta */}
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(255, 255, 255, 0.06)', border: '1px solid rgba(255, 255, 255, 0.12)' }}
                title="Meta"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.51 1.49-3.89 3.78-3.89 1.09 0 2.23.19 2.23.19v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 008.44-9.9c0-5.53-4.5-10.02-10-10.02z" fill="#1877F2"/>
                </svg>
              </div>
              {/* Google */}
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(255, 255, 255, 0.06)', border: '1px solid rgba(255, 255, 255, 0.12)' }}
                title="Google"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              </div>
              {/* TikTok */}
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(255, 255, 255, 0.06)', border: '1px solid rgba(255, 255, 255, 0.12)' }}
                title="TikTok"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none">
                  <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z" fill="#fff"/>
                </svg>
              </div>
              {/* Snapchat */}
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(255, 255, 255, 0.06)', border: '1px solid rgba(255, 255, 255, 0.12)' }}
                title="Snapchat"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none">
                  <path d="M12.21 2c2.93.02 4.65 1.73 5.17 3.62.2.73.15 1.5.15 2.25 0 .56-.04 1.12-.09 1.68.32.15.67.23 1.02.28.54.08 1.13.22 1.13.74 0 .55-.62.72-1.08.82-.17.04-.34.07-.5.12.23.62.65 1.16 1.14 1.6.53.47 1.15.83 1.82 1.08.35.13.88.27.88.73 0 .38-.31.6-.63.74-.61.26-1.29.36-1.93.53-.12.32-.23.75-.5.97-.3.24-.71.22-1.07.32-.46.13-.85.38-1.23.67-.7.52-1.37 1.2-2.29 1.36-.45.08-.91.02-1.36-.08-.71-.16-1.4-.43-2.14-.43-.74 0-1.43.27-2.14.43-.45.1-.91.16-1.36.08-.92-.16-1.59-.84-2.29-1.36-.38-.29-.77-.54-1.23-.67-.36-.1-.77-.08-1.07-.32-.27-.22-.38-.65-.5-.97-.64-.17-1.32-.27-1.93-.53-.32-.14-.63-.36-.63-.74 0-.46.53-.6.88-.73.67-.25 1.29-.61 1.82-1.08.49-.44.91-.98 1.14-1.6-.16-.05-.33-.08-.5-.12-.46-.1-1.08-.27-1.08-.82 0-.52.59-.66 1.13-.74.35-.05.7-.13 1.02-.28-.05-.56-.09-1.12-.09-1.68 0-.75-.05-1.52.15-2.25C5.35 3.73 7.07 2.02 10 2h2.21z" fill="#FFFC00"/>
                </svg>
              </div>
              {/* LinkedIn */}
              <div
                className="w-12 h-12 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(255, 255, 255, 0.06)', border: '1px solid rgba(255, 255, 255, 0.12)' }}
                title="LinkedIn"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" fill="#0A66C2"/>
                </svg>
              </div>
            </div>
            <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              Integrated with Meta, Google, TikTok, Snapchat & more
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-6 mt-12">
            {[
              { value: '150+', label: 'Growth Teams' },
              { value: '$12M+', label: 'Revenue Recovered' },
              { value: '4.2x', label: 'Avg ROAS Lift' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl font-bold" style={{ color: '#f97316' }}>{stat.value}</div>
                <div className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 relative z-10">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
            <div
              className="h-10 w-10 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #f97316 0%, #06b6d4 100%)' }}
            >
              <span className="text-white font-bold text-xl">S</span>
            </div>
            <span
              className="text-2xl font-bold"
              style={{
                background: 'linear-gradient(135deg, #f97316 0%, #06b6d4 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}
            >
              Stratum AI
            </span>
          </div>

          {/* Card */}
          <div
            className="p-8 rounded-2xl"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              backdropFilter: 'blur(20px)'
            }}
          >
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Welcome back</h2>
              <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                Enter your credentials to access your account
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Error message */}
              {error && (
                <div
                  className="flex items-center gap-2 p-3 rounded-lg text-sm"
                  style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}
                >
                  <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Email field */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-white">
                  Email address
                </label>
                <div className="relative">
                  <EnvelopeIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                  />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all"
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)'
                    }}
                    onFocus={(e) => e.target.style.borderColor = '#f97316'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)'}
                    placeholder="name@company.com"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Password field */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-white">
                    Password
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-sm hover:underline"
                    style={{ color: '#f97316' }}
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <LockClosedIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                  />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-12 pr-12 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all"
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)'
                    }}
                    onFocus={(e) => e.target.style.borderColor = '#f97316'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)'}
                    placeholder="Enter your password"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 hover:text-white transition-colors"
                    style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* Remember me */}
              <div className="flex items-center gap-2">
                <input
                  id="remember"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded"
                  style={{ accentColor: '#f97316' }}
                />
                <label htmlFor="remember" className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  Remember me for 30 days
                </label>
              </div>

              {/* Submit button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 rounded-xl font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: '#f97316',
                  boxShadow: '0 4px 20px rgba(252, 100, 35, 0.4)'
                }}
                onMouseOver={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 8px 30px rgba(252, 100, 35, 0.5)'
                  }
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = '0 4px 20px rgba(252, 100, 35, 0.4)'
                }}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.12)' }} />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 text-sm" style={{ background: 'rgba(12, 27, 44, 0.8)', color: 'rgba(255, 255, 255, 0.5)' }}>
                  Or continue with
                </span>
              </div>
            </div>

            {/* Social login */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                className="flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-medium transition-all hover:bg-white/10"
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)'
                }}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Google
              </button>
              <button
                type="button"
                className="flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-medium transition-all hover:bg-white/10"
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)'
                }}
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                Microsoft
              </button>
            </div>

            {/* Demo accounts */}
            <div className="mt-6 pt-6" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.12)' }}>
              <p className="text-center text-sm mb-3" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                Demo Accounts
              </p>
              <div className="grid grid-cols-3 gap-2">
                {['superadmin', 'admin', 'user'].map((role) => (
                  <button
                    key={role}
                    onClick={() => handleDemoLogin(role as any)}
                    disabled={isLoading}
                    className="px-3 py-2 rounded-lg text-xs font-medium capitalize transition-all hover:bg-white/10 disabled:opacity-50"
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      color: 'rgba(255, 255, 255, 0.75)'
                    }}
                  >
                    {role === 'superadmin' ? 'Super Admin' : role}
                  </button>
                ))}
              </div>
            </div>

            {/* Sign up link */}
            <p className="text-center text-sm mt-6" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              Don't have an account?{' '}
              <Link to="/signup" className="font-medium hover:underline" style={{ color: '#f97316' }}>
                Sign up
              </Link>
            </p>
          </div>

          {/* Footer */}
          <p className="text-center text-xs mt-6" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>
            By signing in, you agree to our{' '}
            <a href="#" className="hover:underline" style={{ color: '#f97316' }}>Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="hover:underline" style={{ color: '#f97316' }}>Privacy Policy</a>
          </p>
        </div>
      </div>

      {/* CSS for orb animation */}
      <style>{`
        @keyframes orbFloat {
          0%, 100% { transform: translate(0, 0) scale(1); }
          25% { transform: translate(50px, -50px) scale(1.1); }
          50% { transform: translate(-30px, 30px) scale(0.95); }
          75% { transform: translate(30px, 50px) scale(1.05); }
        }
      `}</style>
    </div>
  )
}
