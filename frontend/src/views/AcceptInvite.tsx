/**
 * Accept Invite Page - Stratum AI
 *
 * Allows invited users to set their password and full name.
 * Reads the invitation token from URL query params, submits to
 * POST /api/v1/auth/accept-invite, then redirects to /login on success.
 *
 * Cyberpunk Dark theme matching Login & Signup pages (bg-[#050B18]).
 */

import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { authStyles } from '@/components/auth/authStyles';

const API_BASE =
  window.__RUNTIME_CONFIG__?.VITE_API_URL ||
  import.meta.env.VITE_API_URL ||
  '/api/v1';

// ── Theme (Cyberpunk Dark) ─────────────────────────────────────────────────
const theme = {
  bgPage: '#050B18',
  bgCard: 'rgba(10, 22, 40, 0.8)',
  bgInput: 'rgba(255, 255, 255, 0.05)',
  primary: '#00c7be',
  primaryHover: '#00b3aa',
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  textPrimary: 'rgba(245, 245, 247, 0.92)',
  textSecondary: 'rgba(245, 245, 247, 0.6)',
  textMuted: 'rgba(245, 245, 247, 0.4)',
  border: 'rgba(255, 255, 255, 0.08)',
  danger: '#ef4444',
  success: '#34c759',
};

// ── Component ──────────────────────────────────────────────────────────────
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

  // ── No token state ───────────────────────────────────────────────────
  if (!token) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: theme.bgPage }}
      >
        <style>{authStyles}</style>

        {/* Ambient orbs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div
            className="auth-float-1 absolute w-[500px] h-[500px] rounded-full opacity-20"
            style={{
              background: 'radial-gradient(circle, rgba(0, 199, 190, 0.3), transparent 70%)',
              top: '-10%',
              right: '-5%',
            }}
          />
        </div>

        <div className="relative max-w-md w-full text-center auth-fade-up">
          <div
            className="auth-glass-card p-8 rounded-2xl"
          >
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: `${theme.danger}20` }}
            >
              <ExclamationTriangleIcon className="w-8 h-8" style={{ color: theme.danger }} />
            </div>
            <h1 className="text-2xl font-semibold mb-3" style={{ color: theme.textPrimary }}>
              Invalid invitation link
            </h1>
            <p className="mb-6 text-sm" style={{ color: theme.textMuted }}>
              This invitation link is invalid or has expired. Please ask your administrator to send a
              new invitation.
            </p>
            <Link
              to="/login"
              className="block w-full py-3 rounded-xl text-black font-semibold text-center transition-all duration-200"
              style={{ background: theme.primary }}
            >
              Go to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Success state ────────────────────────────────────────────────────
  if (isSuccess) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: theme.bgPage }}
      >
        <style>{authStyles}</style>

        {/* Ambient orbs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div
            className="auth-float-2 absolute w-[400px] h-[400px] rounded-full opacity-20"
            style={{
              background: 'radial-gradient(circle, rgba(52, 199, 89, 0.3), transparent 70%)',
              bottom: '10%',
              left: '10%',
            }}
          />
        </div>

        <div className="relative max-w-md w-full text-center auth-fade-up">
          <div className="auth-glass-card p-8 rounded-2xl">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: `${theme.success}20` }}
            >
              <CheckCircleIcon className="w-8 h-8" style={{ color: theme.success }} />
            </div>
            <h1 className="text-2xl font-semibold mb-3" style={{ color: theme.textPrimary }}>
              Account activated
            </h1>
            <p className="mb-6 text-sm" style={{ color: theme.textMuted }}>
              Your account has been set up successfully. You can now sign in with your new password.
            </p>
            <button
              onClick={() => navigate('/login', { state: { inviteAccepted: true } })}
              className="w-full py-3 rounded-xl text-black font-semibold transition-all duration-200"
              style={{ background: theme.primary }}
              onMouseEnter={(e) => (e.currentTarget.style.background = theme.primaryHover)}
              onMouseLeave={(e) => (e.currentTarget.style.background = theme.primary)}
            >
              Sign in
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Form submission ──────────────────────────────────────────────────
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

  // ── Main form ────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ background: theme.bgPage }}
    >
      <style>{authStyles}</style>

      {/* Ambient orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="auth-float-1 absolute w-[600px] h-[600px] rounded-full opacity-15"
          style={{
            background: 'radial-gradient(circle, rgba(0, 199, 190, 0.25), transparent 70%)',
            top: '-15%',
            right: '-10%',
          }}
        />
        <div
          className="auth-float-2 absolute w-[400px] h-[400px] rounded-full opacity-10"
          style={{
            background: 'radial-gradient(circle, rgba(255, 31, 109, 0.2), transparent 70%)',
            bottom: '-5%',
            left: '-5%',
          }}
        />
        {/* Grid mesh */}
        <div className="auth-cyber-grid absolute inset-0" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 mb-8 auth-fade-up">
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center"
            style={{ background: theme.primary }}
          >
            <span className="text-white font-semibold text-lg">S</span>
          </div>
          <span className="text-xl font-semibold" style={{ color: theme.textPrimary }}>
            Stratum AI
          </span>
        </Link>

        {/* Card */}
        <div className="auth-glass-card p-8 rounded-2xl auth-fade-up-d1">
          <h1 className="text-2xl font-semibold mb-2" style={{ color: theme.textPrimary }}>
            Set up your account
          </h1>
          <p className="mb-6 text-sm" style={{ color: theme.textMuted }}>
            You have been invited to join Stratum AI. Complete the form below to activate your
            account.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* API Error */}
            {apiError && (
              <div
                className="flex items-center gap-3 p-4 rounded-xl text-sm auth-slide-in"
                style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  color: theme.danger,
                }}
              >
                <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            {/* Full Name */}
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                style={{ color: theme.textSecondary }}
              >
                Full Name
              </label>
              <div className="relative auth-input-glow rounded-xl">
                <UserIcon
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                  style={{ color: theme.textMuted }}
                />
                <input
                  type="text"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, fullName: true }))}
                  className="w-full pl-12 pr-4 py-3 rounded-xl text-sm outline-none transition-all duration-200"
                  style={{
                    background: theme.bgInput,
                    border: `1px solid ${theme.border}`,
                    color: theme.textPrimary,
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = theme.primary;
                    e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                  }}
                  onBlurCapture={(e) => {
                    e.target.style.borderColor = theme.border;
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>
              {fullNameError && (
                <p className="text-xs" style={{ color: theme.danger }}>
                  {fullNameError}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                style={{ color: theme.textSecondary }}
              >
                Password
              </label>
              <div className="relative auth-input-glow rounded-xl">
                <LockClosedIcon
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                  style={{ color: theme.textMuted }}
                />
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Min. 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
                  className="w-full pl-12 pr-12 py-3 rounded-xl text-sm outline-none transition-all duration-200"
                  style={{
                    background: theme.bgInput,
                    border: `1px solid ${theme.border}`,
                    color: theme.textPrimary,
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = theme.primary;
                    e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                  }}
                  onBlurCapture={(e) => {
                    e.target.style.borderColor = theme.border;
                    e.target.style.boxShadow = 'none';
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: theme.textMuted }}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="w-5 h-5" />
                  ) : (
                    <EyeIcon className="w-5 h-5" />
                  )}
                </button>
              </div>
              {passwordError && (
                <p className="text-xs" style={{ color: theme.danger }}>
                  {passwordError}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                style={{ color: theme.textSecondary }}
              >
                Confirm Password
              </label>
              <div className="relative auth-input-glow rounded-xl">
                <LockClosedIcon
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                  style={{ color: theme.textMuted }}
                />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, confirmPassword: true }))}
                  className="w-full pl-12 pr-12 py-3 rounded-xl text-sm outline-none transition-all duration-200"
                  style={{
                    background: theme.bgInput,
                    border: `1px solid ${theme.border}`,
                    color: theme.textPrimary,
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = theme.primary;
                    e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                  }}
                  onBlurCapture={(e) => {
                    e.target.style.borderColor = theme.border;
                    e.target.style.boxShadow = 'none';
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: theme.textMuted }}
                >
                  {showConfirmPassword ? (
                    <EyeSlashIcon className="w-5 h-5" />
                  ) : (
                    <EyeIcon className="w-5 h-5" />
                  )}
                </button>
              </div>
              {confirmPasswordError && (
                <p className="text-xs" style={{ color: theme.danger }}>
                  {confirmPasswordError}
                </p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl font-semibold text-black transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: theme.primary }}
              onMouseEnter={(e) => {
                if (!isLoading) e.currentTarget.style.background = theme.primaryHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = theme.primary;
              }}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Activating account...
                </span>
              ) : (
                'Activate Account'
              )}
            </button>
          </form>

          {/* Footer link */}
          <p className="text-center text-sm mt-6" style={{ color: theme.textMuted }}>
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-medium transition-colors duration-200 hover:underline"
              style={{ color: theme.primary }}
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
