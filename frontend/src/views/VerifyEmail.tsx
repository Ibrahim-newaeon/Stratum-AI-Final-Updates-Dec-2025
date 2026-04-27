import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle, AlertTriangle, Mail, ArrowRight } from 'lucide-react';
import { useVerifyEmail, useResendVerification } from '@/api/auth';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

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
      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />
        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
              Invalid verification link
            </h2>
            <p className="text-sm text-[#8B92A8] mb-8">
              The verification link is missing or invalid. Check your inbox for the correct link.
            </p>
            <Link
              to="/login"
              className="block w-full bg-[#C9A227] text-[#080C14] font-semibold rounded-lg py-3 hover:bg-[#D4AF37] transition-colors duration-200 text-center"
            >
              Back to login
            </Link>
          </div>
        </section>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />
        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
            <div className="w-16 h-16 rounded-full border-4 border-[#C9A227]/20 border-t-[#C9A227] animate-spin mx-auto mb-6" />
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
              Verifying your email
            </h2>
            <p className="text-sm text-[#8B92A8]">
              Please wait while we verify your email address...
            </p>
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
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
              Email verified
            </h2>
            <p className="text-sm text-[#8B92A8] mb-8">
              Your email has been verified. You can now access your dashboard.
            </p>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 w-full bg-[#C9A227] text-[#080C14] font-semibold rounded-lg py-3 hover:bg-[#D4AF37] transition-colors duration-200"
            >
              Continue to dashboard
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </div>
    );
  }

  // Error state
  return (
    <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
      <AuthLeftPanel />
      <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
          <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
            Verification failed
          </h2>
          <p className="text-sm text-[#8B92A8] mb-8">
            {error || 'The verification link is invalid or has expired.'}
          </p>
          <div className="space-y-4">
            <Link
              to="/signup"
              className="block w-full bg-[#C9A227] text-[#080C14] font-semibold rounded-lg py-3 hover:bg-[#D4AF37] transition-colors duration-200 text-center"
            >
              Create account
            </Link>
            {!showResendForm ? (
              <button
                onClick={() => setShowResendForm(true)}
                className="text-xs text-[#8B92A8] hover:text-[#D4AF37] transition-colors duration-200 font-medium"
              >
                Resend verification
              </button>
            ) : (
              <div className="space-y-3 text-left">
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    type="email"
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    placeholder="Enter your email"
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-4 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#C9A227]/30 focus:border-[#C9A227]/50 transition-colors duration-200"
                  />
                </div>
                <button
                  onClick={async () => {
                    if (!resendEmail) return;
                    resendMutation.mutate(
                      { email: resendEmail },
                      { onSuccess: () => setShowResendForm(false) }
                    );
                  }}
                  disabled={resendMutation.isPending || !resendEmail}
                  className="text-xs text-[#C9A227] hover:text-[#D4AF37] transition-colors duration-200 disabled:opacity-50 font-medium"
                >
                  {resendMutation.isPending
                    ? 'Sending...'
                    : resendMutation.isSuccess
                      ? 'Verification sent!'
                      : 'Send verification'}
                </button>
                {resendMutation.isError && (
                  <p className="text-xs text-red-400">
                    {resendMutation.error?.message || 'Failed to resend verification.'}
                  </p>
                )}
                {resendMutation.isSuccess && (
                  <p className="text-xs text-emerald-400">
                    Verification sent. Check your inbox.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
