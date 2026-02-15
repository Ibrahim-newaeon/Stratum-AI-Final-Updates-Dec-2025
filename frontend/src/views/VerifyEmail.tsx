/**
 * Verify Email Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card verification states
 *
 * States:
 * 1. No token + email param → "Check your email" instructions (post-signup)
 * 2. No token + no email   → Invalid link error with resend form
 * 3. Token present          → Auto-verify loading → success/error
 */

import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  EnvelopeIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useResendVerification, useVerifyEmail } from '@/api/auth';
import { SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

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
    setResendSuccess(false);
    resendMutation.mutate(
      { email: resendEmail },
      { onSuccess: () => setResendSuccess(true) }
    );
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

  // ---------------------------------------------------------------------------
  // Determine which card content to render
  // ---------------------------------------------------------------------------
  let cardContent: React.ReactNode;

  if (!token && emailParam) {
    // Post-signup: "Check your email" instructions
    cardContent = (
      <>
        {/* Back link */}
        <Link
          to="/login"
          className="inline-flex items-center gap-2 text-[12px] font-bold text-white/30 hover:text-[#00c7be] transition-colors mb-6 uppercase tracking-wider"
        >
          <ArrowLeftIcon className="w-3.5 h-3.5" />
          Back to login
        </Link>

        <div className="text-center">
          <div className="w-14 h-14 bg-[#00c7be]/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-[#00c7be]/20">
            <EnvelopeIcon className="w-7 h-7 text-[#00c7be]" />
          </div>
          <h2 className="text-[24px] font-display font-bold text-white mb-2">
            Check your email
          </h2>
          <p className="text-white/40 text-[14px] mb-2">
            We&apos;ve sent a verification link to:
          </p>
          <p className="text-white font-medium text-[14px] mb-6">
            {emailParam}
          </p>
          <p className="text-white/30 text-[13px] mb-8">
            Click the link in the email to verify your account. If you don&apos;t see it, check your spam folder.
          </p>

          {/* Resend */}
          {!resendSuccess ? (
            <button
              onClick={handleResend}
              disabled={resendMutation.isPending}
              className="w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
            >
              {resendMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Sending...
                </span>
              ) : (
                'Resend verification email'
              )}
            </button>
          ) : (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <CheckCircleIcon className="w-6 h-6 mx-auto mb-2 text-emerald-400" />
              <p className="text-emerald-400 text-[13px] font-medium">
                Verification email sent! Check your inbox.
              </p>
            </div>
          )}
        </div>
      </>
    );
  } else if (!token) {
    // No token and no email — invalid link
    cardContent = (
      <div className="text-center">
        <div className="w-14 h-14 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-red-500/20">
          <ExclamationTriangleIcon className="w-7 h-7 text-red-400" />
        </div>
        <h2 className="text-[24px] font-display font-bold text-white mb-2">
          Invalid verification link
        </h2>
        <p className="text-white/40 text-[14px] mb-6">
          The verification link is missing or invalid.
        </p>
        <Link
          to="/login"
          className="block w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px]"
        >
          <ArrowLeftIcon className="w-4 h-4" />
          Back to Login
        </Link>
      </div>
    );
  } else if (isLoading) {
    // Verifying token
    cardContent = (
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 bg-[#00c7be] rounded-lg flex items-center justify-center shadow-lg shadow-[#00c7be]/20">
            <span className="font-display font-bold text-white text-lg">S</span>
          </div>
          <span className="font-display font-bold text-lg tracking-tight text-white">
            Stratum AI
          </span>
        </div>
        <div className="w-12 h-12 rounded-full mx-auto mb-6 animate-spin border-[3px] border-[#00c7be]/20 border-t-[#00c7be]" />
        <h2 className="text-[20px] font-display font-bold text-white mb-2">
          Verifying your email
        </h2>
        <p className="text-white/40 text-[14px]">Please wait...</p>
      </div>
    );
  } else if (isSuccess) {
    // Verified successfully
    cardContent = (
      <div className="text-center">
        <div className="w-14 h-14 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-emerald-500/20">
          <CheckCircleIcon className="w-7 h-7 text-emerald-400" />
        </div>
        <h2 className="text-[24px] font-display font-bold text-white mb-2">
          Email verified!
        </h2>
        <p className="text-white/40 text-[14px] mb-6">
          Your email has been verified. You can now sign in to your account.
        </p>
        <Link
          to="/login"
          className="block w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px]"
        >
          Sign in to Dashboard
          <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </Link>
      </div>
    );
  } else {
    // Error state — verification failed
    cardContent = (
      <>
        {/* Back link */}
        <Link
          to="/login"
          className="inline-flex items-center gap-2 text-[12px] font-bold text-white/30 hover:text-[#00c7be] transition-colors mb-6 uppercase tracking-wider"
        >
          <ArrowLeftIcon className="w-3.5 h-3.5" />
          Back to login
        </Link>

        <div className="text-center">
          <div className="w-14 h-14 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-red-500/20">
            <ExclamationTriangleIcon className="w-7 h-7 text-red-400" />
          </div>
          <h2 className="text-[24px] font-display font-bold text-white mb-2">
            Verification failed
          </h2>
          <p className="text-white/40 text-[14px] mb-6">
            {error || 'The verification link is invalid or has expired.'}
          </p>

          {!resendSuccess ? (
            <div className="space-y-4">
              <p className="text-[13px] text-white/30">
                Enter your email to get a new verification link:
              </p>
              <div className="relative auth-input-glow rounded-xl transition-shadow">
                <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                <input
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                />
              </div>
              <button
                onClick={handleResend}
                disabled={!resendEmail || resendMutation.isPending}
                className="w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
              >
                {resendMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
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
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <CheckCircleIcon className="w-6 h-6 mx-auto mb-2 text-emerald-400" />
              <p className="text-emerald-400 text-[13px] font-medium">
                Verification email sent! Check your inbox.
              </p>
            </div>
          )}
        </div>
      </>
    );
  }

  return (
    <>
      <SEO
        title="Verify Email"
        description="Verify your Stratum AI email address to activate your account."
        noIndex
        url="https://stratum-ai.com/verify-email"
      />
      <style>{authStyles}</style>

      <div className="bg-black text-white min-h-screen flex font-sans selection:bg-[#00c7be]/30 overflow-hidden">
        {/* Background effects — matching landing page Apple Glass Dark */}
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(0, 199, 190, 0.08), transparent 60%)' }} />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(139, 92, 246, 0.06), transparent 60%)' }} />
          <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(20, 240, 198, 0.05), transparent 60%)' }} />
        </div>

        <main className="relative z-10 w-full flex min-h-screen">
          {/* Left Panel — hidden on mobile */}
          <AuthLeftPanel className="hidden lg:flex" />

          {/* Right Panel — Verification Card */}
          <section className="lg:w-5/12 w-full flex items-center justify-center p-6 lg:p-8 bg-black/50 relative">
            {/* Decorative corners — neutral white matching landing page borders */}
            <div className="absolute top-8 right-8 w-16 h-16 border-t border-r border-white/[0.08] pointer-events-none rounded-tr-2xl hidden lg:block" />
            <div className="absolute bottom-8 left-8 w-16 h-16 border-b border-l border-white/[0.08] pointer-events-none rounded-bl-2xl hidden lg:block" />

            {/* Mobile logo */}
            <div className="lg:hidden absolute top-6 left-6 flex items-center gap-3">
              <div className="w-9 h-9 bg-[#00c7be] rounded-lg flex items-center justify-center shadow-lg">
                <span className="font-display font-bold text-white text-base">S</span>
              </div>
              <span className="font-display font-bold text-lg tracking-tight text-white">
                STRATUM AI
              </span>
            </div>

            <div className="w-full max-w-[400px] auth-glass-card rounded-[24px] p-7 shadow-2xl relative z-20 auth-fade-up">
              {cardContent}
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
