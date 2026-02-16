/**
 * Forgot Password Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card form
 * Cyberpunk Dark theme — midnight navy + spectral pink/orange/gold
 *
 * Two-step flow:
 *   Step 1 — Enter email
 *   Step 2 — Choose delivery method (Email or WhatsApp)
 *   Success — Confirmation with method-specific message
 *
 * Fixes applied:
 * - BUG-008: Redesigned to match Login/Signup split-screen layout
 * - BUG-009: Fixed page title (was showing "Sign Up" instead of "Forgot Password")
 * - BUG-010: Added WhatsApp delivery option for password reset link
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
  DevicePhoneMobileIcon,
} from '@heroicons/react/24/outline';
import { useForgotPassword } from '@/api/auth';
import { SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email'),
});

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

type DeliveryMethod = 'email' | 'whatsapp';

export default function ForgotPassword() {
  const [step, setStep] = useState<1 | 2>(1);
  const [submittedEmail, setSubmittedEmail] = useState('');
  const [deliveryMethod, setDeliveryMethod] = useState<DeliveryMethod>('email');
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

  // Step 1 → Step 2: validate email then show delivery method selection
  const onContinue = (data: ForgotPasswordForm) => {
    setSubmittedEmail(data.email);
    setStep(2);
  };

  // Step 2: send reset link with chosen method
  const onSend = () => {
    forgotPasswordMutation.mutate({
      email: submittedEmail,
      delivery_method: deliveryMethod,
    });
  };

  // Reset flow back to step 1
  const resetFlow = () => {
    forgotPasswordMutation.reset();
    setStep(1);
    setDeliveryMethod('email');
    setSubmittedEmail('');
  };

  return (
    <>
      {/* BUG-009: Correct page title */}
      <SEO
        title="Forgot Password"
        description="Reset your Stratum AI password. Choose to receive your reset link via email or WhatsApp."
        noIndex
        url="https://stratum-ai.com/forgot-password"
      />
      <style>{authStyles}</style>

      <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
        {/* Background effects — cyberpunk mesh */}
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
          <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 215, 0, 0.05), transparent 60%)' }} />
        </div>

        <main className="relative z-10 w-full flex min-h-screen">
          {/* Left Panel — hidden on mobile */}
          <AuthLeftPanel className="hidden lg:flex" />

          {/* Right Panel — Form */}
          <section className="lg:w-5/12 w-full flex items-center justify-center p-6 lg:p-8 bg-[#080E1C] relative">
            {/* Subtle gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-bl from-[#FF1F6D]/5 via-transparent to-transparent pointer-events-none" />

            <div className="w-full max-w-[400px] auth-glass-card rounded-xl p-10 shadow-2xl relative z-20 auth-fade-up">
              {isSuccess ? (
                /* ─── Success State ─── */
                <div className="text-center">
                  <div className="w-14 h-14 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-emerald-500/20">
                    <CheckCircleIcon className="w-7 h-7 text-emerald-400" />
                  </div>
                  <h2 className="text-[24px] font-display font-bold text-white mb-2">
                    {deliveryMethod === 'whatsapp' ? 'Check your WhatsApp' : 'Check your email'}
                  </h2>
                  <p className="text-slate-400 text-[14px] mb-2">
                    We&apos;ve sent a password reset link to:
                  </p>
                  <div className="flex items-center justify-center gap-2 mb-6">
                    {deliveryMethod === 'whatsapp' ? (
                      <DevicePhoneMobileIcon className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <EnvelopeIcon className="w-4 h-4 text-emerald-400" />
                    )}
                    <p className="text-white font-medium text-[14px]">
                      {deliveryMethod === 'whatsapp'
                        ? 'Your registered phone number'
                        : submittedEmail}
                    </p>
                  </div>
                  <p className="text-slate-500 text-[13px] mb-8">
                    {deliveryMethod === 'whatsapp'
                      ? 'The link will expire in 1 hour. Open the message on your phone to reset your password.'
                      : "If you don't see it in your inbox, check your spam folder."}
                  </p>

                  <Link
                    to="/login"
                    className="block w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px]"
                  >
                    <ArrowLeftIcon className="w-4 h-4" />
                    Back to Login
                  </Link>

                  <button
                    onClick={resetFlow}
                    className="mt-4 text-[13px] font-bold text-[#FF1F6D] hover:text-white transition-colors"
                  >
                    Try a different email
                  </button>
                </div>
              ) : step === 2 ? (
                /* ─── Step 2: Choose Delivery Method ─── */
                <>
                  {/* Back to step 1 */}
                  <button
                    onClick={() => setStep(1)}
                    className="inline-flex items-center gap-2 text-[12px] font-bold text-slate-500 hover:text-[#FF1F6D] transition-colors mb-6 uppercase tracking-wider"
                  >
                    <ArrowLeftIcon className="w-3.5 h-3.5" />
                    Change email
                  </button>

                  {/* Header */}
                  <div className="mb-6 text-center">
                    <div className="w-14 h-14 bg-[#FF1F6D]/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-[#FF1F6D]/20">
                      <KeyIcon className="w-7 h-7 text-[#FF1F6D]" />
                    </div>
                    <h2 className="text-[24px] font-display font-bold text-white mb-2">
                      Choose Delivery Method
                    </h2>
                    <p className="text-slate-400 text-[14px]">
                      How would you like to receive your reset link?
                    </p>
                  </div>

                  {/* Email being used */}
                  <div className="mb-5 px-3 py-2.5 rounded-xl bg-[rgba(5,11,24,0.6)] border border-white/10">
                    <div className="flex items-center gap-2">
                      <EnvelopeIcon className="w-4 h-4 text-slate-500" />
                      <span className="text-[13px] text-slate-400 truncate">{submittedEmail}</span>
                    </div>
                  </div>

                  {/* API Error */}
                  {apiError && (
                    <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400 mb-4">
                      <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                      <span>{apiError}</span>
                    </div>
                  )}

                  {/* Delivery method cards */}
                  <div className="flex flex-col gap-3 mb-6">
                    {/* Email option */}
                    <button
                      type="button"
                      onClick={() => setDeliveryMethod('email')}
                      className={`w-full flex items-center gap-4 p-4 rounded-xl border transition-all text-left ${
                        deliveryMethod === 'email'
                          ? 'border-[#FF1F6D]/50 bg-[#FF1F6D]/5'
                          : 'border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15]'
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        deliveryMethod === 'email'
                          ? 'bg-[#FF1F6D]/15'
                          : 'bg-white/[0.05]'
                      }`}>
                        <EnvelopeIcon className={`w-5 h-5 ${
                          deliveryMethod === 'email' ? 'text-[#FF1F6D]' : 'text-slate-500'
                        }`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-[14px] font-semibold ${
                          deliveryMethod === 'email' ? 'text-white' : 'text-white/70'
                        }`}>
                          Email
                        </p>
                        <p className="text-[12px] text-slate-500 truncate">
                          Send to {submittedEmail}
                        </p>
                      </div>
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                        deliveryMethod === 'email'
                          ? 'border-[#FF1F6D]'
                          : 'border-white/20'
                      }`}>
                        {deliveryMethod === 'email' && (
                          <div className="w-2.5 h-2.5 rounded-full bg-[#FF1F6D]" />
                        )}
                      </div>
                    </button>

                    {/* WhatsApp option */}
                    <button
                      type="button"
                      onClick={() => setDeliveryMethod('whatsapp')}
                      className={`w-full flex items-center gap-4 p-4 rounded-xl border transition-all text-left ${
                        deliveryMethod === 'whatsapp'
                          ? 'border-[#25D366]/50 bg-[#25D366]/5'
                          : 'border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15]'
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        deliveryMethod === 'whatsapp'
                          ? 'bg-[#25D366]/15'
                          : 'bg-white/[0.05]'
                      }`}>
                        {/* WhatsApp icon */}
                        <svg
                          className={`w-5 h-5 ${deliveryMethod === 'whatsapp' ? 'text-[#25D366]' : 'text-slate-500'}`}
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-[14px] font-semibold ${
                          deliveryMethod === 'whatsapp' ? 'text-white' : 'text-white/70'
                        }`}>
                          WhatsApp
                        </p>
                        <p className="text-[12px] text-slate-500">
                          Send to your registered phone
                        </p>
                      </div>
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                        deliveryMethod === 'whatsapp'
                          ? 'border-[#25D366]'
                          : 'border-white/20'
                      }`}>
                        {deliveryMethod === 'whatsapp' && (
                          <div className="w-2.5 h-2.5 rounded-full bg-[#25D366]" />
                        )}
                      </div>
                    </button>
                  </div>

                  {/* Send button */}
                  <button
                    type="button"
                    onClick={onSend}
                    disabled={isLoading}
                    className="w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
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

                  {/* Bottom Link */}
                  <div className="mt-6 pt-4">
                    <p className="text-center text-[13px] text-slate-500">
                      Remember your password?{' '}
                      <Link
                        to="/login"
                        className="text-[#FF1F6D] font-bold hover:underline"
                      >
                        Sign in
                      </Link>
                    </p>
                  </div>
                </>
              ) : (
                /* ─── Step 1: Enter Email ─── */
                <>
                  {/* Back link */}
                  <Link
                    to="/login"
                    className="inline-flex items-center gap-2 text-[12px] font-bold text-slate-500 hover:text-[#FF1F6D] transition-colors mb-6 uppercase tracking-wider"
                  >
                    <ArrowLeftIcon className="w-3.5 h-3.5" />
                    Back to login
                  </Link>

                  {/* Header */}
                  <div className="mb-8 text-center">
                    <div className="w-14 h-14 bg-[#FF1F6D]/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-[#FF1F6D]/20">
                      <KeyIcon className="w-7 h-7 text-[#FF1F6D]" />
                    </div>
                    <h2 className="text-[24px] font-display font-bold text-white mb-2">
                      Password Recovery
                    </h2>
                    <p className="text-slate-400 text-[14px]">
                      Enter your email to get started
                    </p>
                  </div>

                  {/* Mobile logo */}
                  <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
                    <div className="w-9 h-9 bg-gradient-to-br from-[#FF1F6D] to-[#FF3D00] rounded-lg flex items-center justify-center rotate-45 shadow-[0_0_15px_rgba(255,31,109,0.4)]">
                      <span className="font-display font-bold text-white text-base -rotate-45">✦</span>
                    </div>
                    <span className="font-display font-bold text-lg tracking-tight text-white">
                      STRATUM AI
                    </span>
                  </div>

                  <form onSubmit={handleSubmit(onContinue)} className="flex flex-col gap-4">
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
                        className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1"
                      >
                        Neural Identifier
                      </label>
                      <div className="relative">
                        <input
                          {...register('email')}
                          id="forgot-email"
                          type="email"
                          autoComplete="email"
                          placeholder="you@company.com"
                          className="w-full h-[44px] px-4 rounded-[12px] text-white placeholder:text-slate-600 focus:ring-0 bg-[rgba(5,11,24,0.6)] border border-white/10 transition-all focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.2)] outline-none text-[14px]"
                        />
                        <EnvelopeIcon className="absolute right-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600" />
                      </div>
                      {errors.email && (
                        <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                      )}
                    </div>

                    {/* Continue Button */}
                    <button
                      type="submit"
                      className="auth-fade-up-d2 w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-2 text-[14px]"
                    >
                      Continue
                      <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                      </svg>
                    </button>
                  </form>

                  {/* Bottom Link */}
                  <div className="mt-6 pt-4">
                    <p className="text-center text-[13px] text-slate-500">
                      Remember your password?{' '}
                      <Link
                        to="/login"
                        className="text-[#FF1F6D] font-bold hover:underline"
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
