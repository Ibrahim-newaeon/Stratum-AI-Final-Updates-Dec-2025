import { useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useVerifyEmail } from '@/api/auth';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const verifyMutation = useVerifyEmail();

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
            <button
              onClick={async () => {
                // TODO: Implement resend verification
                console.log('Resend verification');
              }}
              className="text-meta text-stratum-400 hover:text-stratum-300 transition-colors"
            >
              Resend verification email
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
