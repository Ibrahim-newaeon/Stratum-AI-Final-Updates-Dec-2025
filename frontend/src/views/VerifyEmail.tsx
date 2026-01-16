import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline';
import { useVerifyEmail, useResendVerification } from '@/api/auth';

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
  const error = verifyMutation.error?.message ||
    (verifyMutation.isError ? 'Verification failed' : '');

  const handleResend = () => {
    if (!resendEmail) return;

    resendMutation.mutate(
      { email: resendEmail },
      {
        onSuccess: () => {
          setResendSuccess(true);
        },
      }
    );
  };

  useEffect(() => {
    if (token && !verifyMutation.isPending && !verifyMutation.isSuccess && !verifyMutation.isError) {
      verifyMutation.mutate({ token });
    }
  }, [token]);

  // No token provided
  if (!token) {
    return (
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            <div className="w-20 h-20 rounded-full bg-danger/10 flex items-center justify-center mx-auto mb-6">
              <ExclamationTriangleIcon className="w-10 h-10 text-danger" />
            </div>
            <h1 className="text-h1 text-white mb-4">Invalid verification link</h1>
            <p className="text-body text-text-secondary mb-8">
              The verification link is missing or invalid. Please check your email for the correct link.
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body text-center
                         hover:shadow-glow transition-all duration-base"
            >
              Back to login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            {/* Logo */}
            <div className="flex items-center justify-center gap-2 mb-12">
              <div className="w-10 h-10 rounded-lg bg-gradient-stratum flex items-center justify-center">
                <span className="text-white font-bold text-h3">S</span>
              </div>
              <span className="text-h2 text-white font-semibold">Stratum AI</span>
            </div>

            {/* Loading spinner */}
            <div className="w-16 h-16 rounded-full border-4 border-stratum-500/20 border-t-stratum-500 animate-spin mx-auto mb-6" />

            <h1 className="text-h2 text-white mb-2">Verifying your email</h1>
            <p className="text-body text-text-secondary">
              Please wait while we verify your email address...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            <div className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-6">
              <CheckCircleIcon className="w-10 h-10 text-success" />
            </div>
            <h1 className="text-h1 text-white mb-4">Email verified!</h1>
            <p className="text-body text-text-secondary mb-8">
              Your email has been successfully verified. You can now sign in to your account.
            </p>
            <Link
              to="/login"
              className="inline-block w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body text-center
                         hover:shadow-glow transition-all duration-base"
            >
              Sign in to your account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center">
        <div className="motion-enter">
          <div className="w-20 h-20 rounded-full bg-danger/10 flex items-center justify-center mx-auto mb-6">
            <ExclamationTriangleIcon className="w-10 h-10 text-danger" />
          </div>
          <h1 className="text-h1 text-white mb-4">Verification failed</h1>
          <p className="text-body text-text-secondary mb-6">
            {error || 'The verification link is invalid or has expired.'}
          </p>

          {/* Resend form */}
          {!resendSuccess ? (
            <div className="space-y-4 mb-6">
              <p className="text-meta text-text-muted">
                Enter your email to receive a new verification link:
              </p>
              <div className="relative">
                <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full pl-12 pr-4 py-3 rounded-xl bg-surface-secondary border border-white/10
                             text-white placeholder-text-muted text-body
                             focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                             transition-all duration-base outline-none"
                />
              </div>
              <button
                onClick={handleResend}
                disabled={!resendEmail || resendMutation.isPending}
                className="w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body
                           hover:shadow-glow transition-all duration-base
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {resendMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Sending...
                  </span>
                ) : (
                  'Resend verification email'
                )}
              </button>
            </div>
          ) : (
            <div className="mb-6 p-4 rounded-xl bg-success/10 border border-success/20">
              <CheckCircleIcon className="w-6 h-6 text-success mx-auto mb-2" />
              <p className="text-body text-success">
                Verification email sent! Check your inbox.
              </p>
            </div>
          )}

          <Link
            to="/login"
            className="text-meta text-stratum-400 hover:text-stratum-300 transition-colors"
          >
            Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
