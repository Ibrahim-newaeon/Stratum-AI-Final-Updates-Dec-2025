/**
 * Forgot Password Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card form
 *
 * Fixes applied:
 * - BUG-008: Redesigned to match Login/Signup split-screen layout
 * - BUG-009: Fixed page title (was showing "Sign Up" instead of "Forgot Password")
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { useForgotPassword } from '@/api/auth';
import { SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email'),
});

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPassword() {
  const [submittedEmail, setSubmittedEmail] = useState('');
  const forgotPasswordMutation = useForgotPassword();

  const isLoading = forgotPasswordMutation.isPending;
  const isSuccess = forgotPasswordMutation.isSuccess;
  const apiError = forgotPasswordMutation.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordForm) => {
    setSubmittedEmail(data.email);
    forgotPasswordMutation.mutate({ email: data.email });
  };

  return (
    <>
      {/* BUG-009: Correct page title */}
      <SEO
        title="Forgot Password"
        description="Reset your Stratum AI password. Enter your email to receive a reset link."
        noIndex
        url="https://stratum-ai.com/forgot-password"
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

          {/* Right Panel — Form */}
          <section className="lg:w-5/12 w-full flex items-center justify-center p-6 lg:p-8 bg-black/50 relative">
            {/* Decorative corners — neutral white matching landing page borders */}
            <div className="absolute top-8 right-8 w-16 h-16 border-t border-r border-white/[0.08] pointer-events-none rounded-tr-2xl hidden lg:block" />
            <div className="absolute bottom-8 left-8 w-16 h-16 border-b border-l border-white/[0.08] pointer-events-none rounded-bl-2xl hidden lg:block" />

            <div className="w-full max-w-[400px] auth-glass-card rounded-[24px] p-7 shadow-2xl relative z-20 auth-fade-up">
              {isSuccess ? (
                /* Success State */
                <div className="text-center">
                  <div className="w-14 h-14 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-emerald-500/20">
                    <CheckCircleIcon className="w-7 h-7 text-emerald-400" />
                  </div>
                  <h2 className="text-[24px] font-display font-bold text-white mb-2">
                    Check your email
                  </h2>
                  <p className="text-white/40 text-[14px] mb-2">
                    We&apos;ve sent a password reset link to:
                  </p>
                  <p className="text-white font-medium text-[14px] mb-6">
                    {submittedEmail}
                  </p>
                  <p className="text-white/30 text-[13px] mb-8">
                    If you don&apos;t see it in your inbox, check your spam folder.
                  </p>

                  <Link
                    to="/login"
                    className="block w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px]"
                  >
                    <ArrowLeftIcon className="w-4 h-4" />
                    Back to Login
                  </Link>

                  <button
                    onClick={() => forgotPasswordMutation.reset()}
                    className="mt-4 text-[13px] font-bold text-[#00c7be] hover:text-white transition-colors"
                  >
                    Try a different email
                  </button>
                </div>
              ) : (
                /* Form State */
                <>
                  {/* Back link */}
                  <Link
                    to="/login"
                    className="inline-flex items-center gap-2 text-[12px] font-bold text-white/30 hover:text-[#00c7be] transition-colors mb-6 uppercase tracking-wider"
                  >
                    <ArrowLeftIcon className="w-3.5 h-3.5" />
                    Back to login
                  </Link>

                  {/* Header */}
                  <div className="mb-8 text-center">
                    <div className="w-14 h-14 bg-[#00c7be]/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-[#00c7be]/20">
                      <KeyIcon className="w-7 h-7 text-[#00c7be]" />
                    </div>
                    <h2 className="text-[24px] font-display font-bold text-white mb-2">
                      Password Recovery
                    </h2>
                    <p className="text-white/40 text-[14px]">
                      Enter your email and we&apos;ll send you a reset link
                    </p>
                  </div>

                  {/* Mobile logo */}
                  <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
                    <div className="w-9 h-9 bg-[#00c7be] rounded-lg flex items-center justify-center shadow-lg">
                      <span className="font-display font-bold text-white text-base">S</span>
                    </div>
                    <span className="font-display font-bold text-lg tracking-tight text-white">
                      STRATUM AI
                    </span>
                  </div>

                  <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
                    {/* API Error Alert */}
                    {apiError && (
                      <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400">
                        <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                        <span>{apiError}</span>
                      </div>
                    )}

                    {/* Email */}
                    <div className="auth-fade-up-d1">
                      <label
                        htmlFor="forgot-email"
                        className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                      >
                        Work Identity
                      </label>
                      <div className="relative auth-input-glow rounded-xl transition-shadow">
                        <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                        <input
                          {...register('email')}
                          id="forgot-email"
                          type="email"
                          autoComplete="email"
                          placeholder="you@company.com"
                          className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                        />
                      </div>
                      {errors.email && (
                        <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                      )}
                    </div>

                    {/* Submit Button */}
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="auth-fade-up-d2 w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-2 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
                    >
                      {isLoading ? (
                        <span className="flex items-center gap-2">
                          <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Sending...
                        </span>
                      ) : (
                        <>
                          Send reset link
                          <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                          </svg>
                        </>
                      )}
                    </button>
                  </form>

                  {/* Bottom Link */}
                  <div className="mt-6 pt-4">
                    <p className="text-center text-[13px] text-white/30">
                      Remember your password?{' '}
                      <Link
                        to="/login"
                        className="text-[#00c7be] font-bold hover:underline"
                      >
                        Sign in
                      </Link>
                    </p>
                  </div>
                </>
              )}
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
