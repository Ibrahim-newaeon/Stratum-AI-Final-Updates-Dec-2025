/**
 * Accept Invite Page - Stratum AI
 *
 * Allows invited users to set their password and full name.
 * Reads the invitation token from URL query params, submits to
 * POST /api/v1/auth/accept-invite, then redirects to /login on success.
 */

import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, AlertCircle, AlertTriangle, Eye, EyeOff, Lock, User } from 'lucide-react';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

const API_BASE =
  window.__RUNTIME_CONFIG__?.VITE_API_URL ||
  import.meta.env.VITE_API_URL ||
  '/api/v1';

export default function AcceptInvite() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  // Form state
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Submission state
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [apiError, setApiError] = useState('');

  // Validation
  const [touched, setTouched] = useState<{
    fullName?: boolean;
    password?: boolean;
    confirmPassword?: boolean;
  }>({});

  const fullNameError =
    touched.fullName && !fullName.trim() ? 'Full name is required' : '';
  const passwordError =
    touched.password && !password
      ? 'Password is required'
      : touched.password && password.length > 0 && password.length < 8
        ? 'Password must be at least 8 characters'
        : '';
  const confirmPasswordError =
    touched.confirmPassword && !confirmPassword
      ? 'Please confirm your password'
      : touched.confirmPassword && confirmPassword && confirmPassword !== password
        ? "Passwords don't match"
        : '';

  // No token state
  if (!token) {
    return (
      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />
        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h1 className="text-2xl font-semibold text-[#F0EDE5] mb-3">
              Invalid invitation link
            </h1>
            <p className="text-sm text-[#8B92A8] mb-8">
              This invitation link is invalid or has expired. Please ask your administrator to send a new invitation.
            </p>
            <Link
              to="/login"
              className="block w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 text-center"
            >
              Go to login
            </Link>
          </div>
        </section>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />
        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-semibold text-[#F0EDE5] mb-3">
              Account activated
            </h1>
            <p className="text-sm text-[#8B92A8] mb-8">
              Your account has been set up successfully. You can now sign in with your new password.
            </p>
            <button
              onClick={() => navigate('/login', { state: { inviteAccepted: true } })}
              className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200"
            >
              Sign in
            </button>
          </div>
        </section>
      </div>
    );
  }

  // Form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError('');

    // Mark all fields touched for validation
    setTouched({ fullName: true, password: true, confirmPassword: true });

    // Client-side validation
    if (!fullName.trim() || !password || !confirmPassword) {
      setApiError('Please fill in all fields');
      return;
    }
    if (password.length < 8) {
      setApiError('Password must be at least 8 characters');
      return;
    }
    if (password !== confirmPassword) {
      setApiError("Passwords don't match");
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/auth/accept-invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          full_name: fullName.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        let errorMessage = 'Failed to accept invitation';
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            errorMessage = data.detail[0].msg || data.detail[0].message || 'Validation error';
          } else if (typeof data.detail === 'object' && data.detail.msg) {
            errorMessage = data.detail.msg;
          }
        }
        setApiError(errorMessage);
        return;
      }

      setIsSuccess(true);
    } catch {
      setApiError('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Main form
  return (
    <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
      <AuthLeftPanel />

      <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
        {/* Mobile logo */}
        <div className="lg:hidden mb-8">
          <img
            src="/images/stratum-logo.png"
            alt="Stratum AI"
            className="h-8"
            
            loading="lazy"
            decoding="async"
          />
        </div>

        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
          <h1 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
            Join your team
          </h1>
          <p className="text-sm text-[#8B92A8] mb-6">
            You've been invited to Stratum AI. Set up your account to get started.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* API Error */}
            {apiError && (
              <div className="flex items-center gap-2 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            {/* Full Name */}
            <div className="space-y-2">
              <label htmlFor="invite-name" className="text-xs font-medium text-[#8B92A8] ml-1">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                <input
                  type="text"
                  id="invite-name"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, fullName: true }))}
                  className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-4 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                />
              </div>
              {fullNameError && (
                <p className="text-xs text-red-400 ml-1">{fullNameError}</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label htmlFor="invite-password" className="text-xs font-medium text-[#8B92A8] ml-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="invite-password"
                  placeholder="Min. 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
                  className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-11 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#5A6278] hover:text-[#8B92A8] transition-colors duration-200"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {passwordError && (
                <p className="text-xs text-red-400 ml-1">{passwordError}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label htmlFor="invite-confirm-password" className="text-xs font-medium text-[#8B92A8] ml-1">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  id="invite-confirm-password"
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, confirmPassword: true }))}
                  className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-11 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#5A6278] hover:text-[#8B92A8] transition-colors duration-200"
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {confirmPasswordError && (
                <p className="text-xs text-red-400 ml-1">{confirmPasswordError}</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Activating account...
                </span>
              ) : (
                'Activate Account'
              )}
            </button>
          </form>

          {/* Footer link */}
          <p className="text-center text-sm mt-6 text-[#5A6278]">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 font-medium"
            >
              Sign in
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}

