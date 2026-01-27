/**
 * Verify Email Page - APPLE STYLE LIGHT EDITION
 * Clean white + blue accent + professional
 */

import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  EnvelopeIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useResendVerification, useVerifyEmail } from '@/api/auth';

// Apple Style Theme
const theme = {
  blue: '#007AFF',
  blueHover: '#0056CC',
  blueLight: '#E8F4FF',
  bgBase: '#FFFFFF',
  bgElevated: '#F5F5F7',
  bgSurface: '#FFFFFF',
  textPrimary: '#1D1D1F',
  textSecondary: '#424245',
  textMuted: '#86868B',
  border: 'rgba(0, 0, 0, 0.08)',
  success: '#34C759',
  danger: '#FF3B30',
};

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const emailParam = searchParams.get('email');

  const [resendEmail, setResendEmail] = useState(emailParam || '');
  const [resendSuccess, setResendSuccess] = useState(false);

  const verifyMutation = useVerifyEmail();
  const resendMutation = useResendVerification();

  const isLoading = verifyMutation.isPending;
  const isSuccess = verifyMutation.isSuccess;
  const error =
    verifyMutation.error?.message || (verifyMutation.isError ? 'Verification failed' : '');

  const handleResend = () => {
    if (!resendEmail) return;
    resendMutation.mutate({ email: resendEmail }, { onSuccess: () => setResendSuccess(true) });
  };

  useEffect(() => {
    if (
      token &&
      !verifyMutation.isPending &&
      !verifyMutation.isSuccess &&
      !verifyMutation.isError
    ) {
      verifyMutation.mutate({ token });
    }
  }, [token]);

  // No token
  if (!token) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: theme.bgElevated }}
      >
        <div className="max-w-md w-full text-center">
          <div
            className="p-8 rounded-2xl"
            style={{
              background: theme.bgSurface,
              border: `1px solid ${theme.border}`,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            }}
          >
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: '#FEF2F2' }}
            >
              <ExclamationTriangleIcon className="w-8 h-8" style={{ color: theme.danger }} />
            </div>
            <h1 className="text-2xl font-semibold mb-3" style={{ color: theme.textPrimary }}>
              Invalid verification link
            </h1>
            <p className="mb-6" style={{ color: theme.textMuted }}>
              The verification link is missing or invalid.
            </p>
            <Link
              to="/login"
              className="block w-full py-3 rounded-xl text-white font-semibold text-center transition-all duration-200"
              style={{ background: theme.blue }}
            >
              Back to login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Loading
  if (isLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: theme.bgElevated }}
      >
        <div className="max-w-md w-full text-center">
          <div
            className="p-8 rounded-2xl"
            style={{
              background: theme.bgSurface,
              border: `1px solid ${theme.border}`,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            }}
          >
            <div className="flex items-center justify-center gap-3 mb-8">
              <div
                className="h-10 w-10 rounded-xl flex items-center justify-center"
                style={{ background: theme.blue }}
              >
                <span className="text-white font-semibold text-lg">S</span>
              </div>
              <span className="text-xl font-semibold" style={{ color: theme.textPrimary }}>
                Stratum AI
              </span>
            </div>
            <div
              className="w-12 h-12 rounded-full mx-auto mb-6 animate-spin"
              style={{
                border: `3px solid ${theme.blueLight}`,
                borderTopColor: theme.blue,
              }}
            />
            <h1 className="text-xl font-semibold mb-2" style={{ color: theme.textPrimary }}>
              Verifying your email
            </h1>
            <p style={{ color: theme.textMuted }}>Please wait...</p>
          </div>
        </div>
      </div>
    );
  }

  // Success
  if (isSuccess) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: theme.bgElevated }}
      >
        <div className="max-w-md w-full text-center">
          <div
            className="p-8 rounded-2xl"
            style={{
              background: theme.bgSurface,
              border: `1px solid ${theme.border}`,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            }}
          >
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: `${theme.success}15` }}
            >
              <CheckCircleIcon className="w-8 h-8" style={{ color: theme.success }} />
            </div>
            <h1 className="text-2xl font-semibold mb-3" style={{ color: theme.textPrimary }}>
              Email verified!
            </h1>
            <p className="mb-6" style={{ color: theme.textMuted }}>
              Your email has been verified. You can now sign in.
            </p>
            <Link
              to="/login"
              className="block w-full py-3 rounded-xl text-white font-semibold text-center transition-all duration-200"
              style={{ background: theme.blue }}
              onMouseEnter={(e) => (e.currentTarget.style.background = theme.blueHover)}
              onMouseLeave={(e) => (e.currentTarget.style.background = theme.blue)}
            >
              Sign in to your account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Error
  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ background: theme.bgElevated }}
    >
      <div className="max-w-md w-full text-center">
        <div
          className="p-8 rounded-2xl"
          style={{
            background: theme.bgSurface,
            border: `1px solid ${theme.border}`,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
          }}
        >
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
            style={{ background: '#FEF2F2' }}
          >
            <ExclamationTriangleIcon className="w-8 h-8" style={{ color: theme.danger }} />
          </div>
          <h1 className="text-2xl font-semibold mb-3" style={{ color: theme.textPrimary }}>
            Verification failed
          </h1>
          <p className="mb-6" style={{ color: theme.textMuted }}>
            {error || 'The verification link is invalid or has expired.'}
          </p>

          {!resendSuccess ? (
            <div className="space-y-4">
              <p className="text-sm" style={{ color: theme.textMuted }}>
                Enter your email to get a new link:
              </p>
              <div className="relative">
                <EnvelopeIcon
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                  style={{ color: theme.textMuted }}
                />
                <input
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-12 pr-4 py-3 rounded-xl outline-none transition-all duration-200"
                  style={{
                    background: theme.bgElevated,
                    border: `1px solid ${theme.border}`,
                    color: theme.textPrimary,
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = theme.blue;
                    e.target.style.boxShadow = `0 0 0 3px ${theme.blueLight}`;
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = theme.border;
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>
              <button
                onClick={handleResend}
                disabled={!resendEmail || resendMutation.isPending}
                className="w-full py-3 rounded-xl text-white font-semibold disabled:opacity-50 transition-all duration-200"
                style={{ background: theme.blue }}
                onMouseEnter={(e) => {
                  if (!resendMutation.isPending) e.currentTarget.style.background = theme.blueHover;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = theme.blue;
                }}
              >
                {resendMutation.isPending ? 'Sending...' : 'Resend verification email'}
              </button>
            </div>
          ) : (
            <div className="p-4 rounded-xl" style={{ background: `${theme.success}15` }}>
              <CheckCircleIcon className="w-6 h-6 mx-auto mb-2" style={{ color: theme.success }} />
              <p style={{ color: theme.success }}>Verification email sent!</p>
            </div>
          )}

          <Link
            to="/login"
            className="inline-block mt-6 text-sm font-medium transition-colors hover:underline"
            style={{ color: theme.blue }}
          >
            Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
