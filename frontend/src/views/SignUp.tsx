/**
 * Sign Up Page
 * Tenant self-service registration for Stratum AI
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  Mail,
  User
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function SignUp() {
  const navigate = useNavigate()
  const { setUser, setTokens } = useAuth()

  const [formData, setFormData] = useState({
    company_name: '',
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [agreeToTerms, setAgreeToTerms] = useState(false)

  // Personal email domains that are not allowed
  const blockedEmailDomains = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com', 'yandex.com',
    'gmx.com', 'live.com', 'msn.com', 'me.com', 'qq.com', '163.com'
  ]

  const getEmailDomain = (email: string) => {
    const parts = email.split('@')
    return parts.length === 2 ? parts[1].toLowerCase() : ''
  }

  const isWorkEmail = formData.email ? !blockedEmailDomains.includes(getEmailDomain(formData.email)) : true

  const passwordRequirements = [
    { label: 'At least 8 characters', met: formData.password.length >= 8 },
    { label: 'One uppercase letter', met: /[A-Z]/.test(formData.password) },
    { label: 'One lowercase letter', met: /[a-z]/.test(formData.password) },
    { label: 'One number', met: /\d/.test(formData.password) },
  ]

  const isPasswordValid = passwordRequirements.every((req) => req.met)
  const doPasswordsMatch = formData.password === formData.confirmPassword && formData.confirmPassword.length > 0

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!isWorkEmail) {
      setError('Please use your work email. Personal email addresses are not accepted.')
      return
    }

    if (!isPasswordValid) {
      setError('Password does not meet requirements')
      return
    }

    if (!doPasswordsMatch) {
      setError('Passwords do not match')
      return
    }

    if (!agreeToTerms) {
      setError('Please agree to the Terms of Service and Privacy Policy')
      return
    }

    setIsLoading(true)

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/signup`, {
        company_name: formData.company_name,
        full_name: formData.full_name,
        email: formData.email,
        password: formData.password,
      })

      if (response.data.success) {
        const { user: apiUser, access_token, refresh_token } = response.data.data

        // Map API user to frontend User interface
        const tenant = response.data.data.tenant
        const mappedUser = {
          id: String(apiUser.id),
          email: apiUser.email,
          name: apiUser.full_name,
          role: apiUser.role as 'superadmin' | 'admin' | 'user',
          organization: tenant?.name,
          permissions: apiUser.role === 'admin' ? ['campaigns', 'analytics', 'users'] : ['campaigns', 'analytics'],
          plan: tenant?.plan,
          planExpiresAt: tenant?.plan_expires_at,
        }

        // Store tokens and user
        setTokens(access_token, refresh_token)
        setUser(mappedUser)

        // Navigate to CAPI Setup for onboarding (connect ad platforms first)
        navigate('/app/capi-setup', { replace: true })
      } else {
        setError(response.data.error || 'Sign up failed')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || 'An unexpected error occurred'
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-stratum relative overflow-hidden">
        <div className="absolute inset-0 bg-black/20" />
        <div className="relative z-10 flex flex-col justify-between p-12 text-white">
          <div>
            <Link to="/" className="flex items-center gap-3 mb-8 hover:opacity-80 transition-opacity">
              <div className="h-12 w-12 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center shadow-glow">
                <span className="text-white font-bold text-2xl">S</span>
              </div>
              <span className="text-3xl font-bold">Stratum AI</span>
            </Link>
            <h1 className="text-4xl font-bold mb-4 leading-tight">
              Start Your Free Trial
              <br />
              Today
            </h1>
            <p className="text-lg text-white/80 max-w-md">
              Join thousands of marketing teams using Stratum AI to maximize their advertising ROI across all platforms.
            </p>
          </div>

          <div className="space-y-6">
            <div className="space-y-4">
              {[
                'Unified analytics across 5+ platforms',
                'AI-powered budget optimization',
                'Automated campaign rules',
                'Real-time competitor insights',
              ].map((feature, index) => (
                <div key={index} className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-white/80" />
                  <span className="text-white/80">{feature}</span>
                </div>
              ))}
            </div>

            <p className="text-sm text-white/60">
              No credit card required. 14-day free trial.
            </p>
          </div>

          {/* Decorative elements */}
          <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute -bottom-40 -left-20 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
        </div>
      </div>

      {/* Right side - Sign Up Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background overflow-y-auto">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-lg bg-gradient-stratum flex items-center justify-center shadow-glow">
                <span className="text-white font-bold text-xl">S</span>
              </div>
              <span className="text-2xl font-bold bg-gradient-stratum bg-clip-text text-transparent">
                Stratum AI
              </span>
            </Link>
          </div>

          <Link
            to="/"
            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>

          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-2">Create your account</h2>
            <p className="text-muted-foreground">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Company name */}
            <div className="space-y-2">
              <label htmlFor="company_name" className="text-sm font-medium">
                Company Name
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="company_name"
                  name="company_name"
                  type="text"
                  value={formData.company_name}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  placeholder="Acme Inc."
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Full name */}
            <div className="space-y-2">
              <label htmlFor="full_name" className="text-sm font-medium">
                Your Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  value={formData.full_name}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  placeholder="John Doe"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Email */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Work Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  placeholder="john@yourcompany.com"
                  required
                  disabled={isLoading}
                />
              </div>
              {formData.email && !isWorkEmail ? (
                <p className="text-xs text-destructive flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Personal emails are not accepted. Please use your work email.
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Please use your company email. Personal emails (Gmail, Yahoo, Hotmail, etc.) are not accepted.
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full pl-10 pr-12 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  placeholder="Create a strong password"
                  required
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>

              {/* Password requirements */}
              {formData.password && (
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {passwordRequirements.map((req) => (
                    <div
                      key={req.label}
                      className={cn(
                        'flex items-center gap-1 text-xs',
                        req.met ? 'text-green-600' : 'text-muted-foreground'
                      )}
                    >
                      <CheckCircle className={cn('w-3 h-3', req.met ? 'text-green-600' : 'text-muted-foreground')} />
                      {req.label}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className={cn(
                    'w-full pl-10 pr-4 py-3 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors',
                    formData.confirmPassword && !doPasswordsMatch && 'border-destructive'
                  )}
                  placeholder="Confirm your password"
                  required
                  disabled={isLoading}
                />
              </div>
              {formData.confirmPassword && !doPasswordsMatch && (
                <p className="text-xs text-destructive">Passwords do not match</p>
              )}
              {doPasswordsMatch && (
                <p className="text-xs text-green-600 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Passwords match
                </p>
              )}
            </div>

            {/* Terms agreement */}
            <div className="flex items-start gap-2">
              <input
                id="terms"
                type="checkbox"
                checked={agreeToTerms}
                onChange={(e) => setAgreeToTerms(e.target.checked)}
                className="mt-1 w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor="terms" className="text-sm text-muted-foreground">
                I agree to the{' '}
                <a href="#" className="text-primary hover:underline">
                  Terms of Service
                </a>{' '}
                and{' '}
                <a href="#" className="text-primary hover:underline">
                  Privacy Policy
                </a>
              </label>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading || !isWorkEmail || !isPasswordValid || !doPasswordsMatch || !agreeToTerms}
              className={cn(
                'w-full py-3 rounded-lg font-semibold text-white bg-gradient-stratum shadow-glow transition-all',
                'hover:shadow-glow-lg hover:scale-[1.02]',
                'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100'
              )}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating account...
                </span>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-xs text-muted-foreground mt-8">
            By signing up, you agree to receive marketing communications from Stratum AI.
            You can unsubscribe at any time.
          </p>
        </div>
      </div>
    </div>
  )
}
