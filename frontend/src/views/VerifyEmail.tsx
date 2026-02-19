import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useVerifyEmail, useResendVerification } from '@/api/auth';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const verifyMutation = useVerifyEmail();
  const resendMutation = useResendVerification();
  const [resendEmail, setResendEmail] = useState(searchParams.get('email') || '');
  const [showResendForm, setShowResendForm] = useState(false);

  const isLoading = verifyMutation.isPending;
  const isSuccess = verifyMutation.isSuccess;
  const error = verifyMutation.error?.message ||
    (verifyMutation.isError ? 'Verification failed' : '');

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
          <p className="text-body text-text-secondary mb-8">
            {error || 'The verification link is invalid or has expired.'}
          </p>
          <div className="space-y-4">
            <Link
              to="/signup"
              className="block w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body text-center
                         hover:shadow-glow transition-all duration-base"
            >
              Sign up again
            </Link>
            {!showResendForm ? (
              <button
                onClick={() => setShowResendForm(true)}
                className="text-meta text-stratum-400 hover:text-stratum-300 transition-colors"
              >
                Resend verification email
              </button>
            ) : (
              <div className="space-y-3">
                <input
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="Enter your email address"
                  className="w-full px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white text-sm placeholder:text-text-muted focus:outline-none focus:border-stratum-500"
                />
                <button
                  onClick={async () => {
                    if (!resendEmail) return;
                    resendMutation.mutate(
                      { email: resendEmail },
                      {
                        onSuccess: () => {
                          setShowResendForm(false);
                        },
                      }
                    );
                  }}
                  disabled={resendMutation.isPending || !resendEmail}
                  className="text-meta text-stratum-400 hover:text-stratum-300 transition-colors disabled:opacity-50"
                >
                  {resendMutation.isPending
                    ? 'Sending...'
                    : resendMutation.isSuccess
                      ? 'Verification email sent!'
                      : 'Send verification email'}
                </button>
                {resendMutation.isError && (
                  <p className="text-xs text-danger">
                    {resendMutation.error?.message || 'Failed to resend verification email.'}
                  </p>
                )}
                {resendMutation.isSuccess && (
                  <p className="text-xs text-success">
                    Verification email sent. Please check your inbox.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
