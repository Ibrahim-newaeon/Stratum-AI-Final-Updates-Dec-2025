/**
 * Signup Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card registration form
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  EnvelopeIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  IdentificationIcon,
  LockClosedIcon,
  UserPlusIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';
import { useSignup } from '@/api/auth';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

// ---------------------------------------------------------------------------
// Zod Schema
// ---------------------------------------------------------------------------
const signupSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email'),
  company: z.string().min(2, 'Company name is required'),
  website: z.string().min(4, 'Company website is required'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  termsAccepted: z.literal(true, {
    errorMap: () => ({ message: 'You must accept the terms to continue' }),
  }),
});

type SignupForm = z.infer<typeof signupSchema>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function Signup() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  const registerMutation = useSignup();
  const isLoading = registerMutation.isPending;
  const apiError = registerMutation.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { termsAccepted: false as unknown as true },
  });

  // BUG-005: termsAccepted is now part of Zod schema — validation shows alongside other field errors
  const termsAccepted = watch('termsAccepted');

  const onSubmit = async (data: SignupForm) => {
    registerMutation.mutate(
      {
        email: data.email,
        password: data.password,
        full_name: data.name,
        company_name: data.company,
        company_website: data.website,
      },
      {
        onSuccess: (_data, variables) => {
          navigate(`/verify-email?email=${encodeURIComponent(variables.email)}`);
        },
      }
    );
  };

  return (
    <>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />
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

            <div className="w-full max-w-[448px] auth-glass-card rounded-[24px] p-7 shadow-2xl relative z-20 auth-fade-up">
              {/* Header */}
              <div className="mb-8 text-center">
                <div className="w-14 h-14 bg-[#00c7be]/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-[#00c7be]/20">
                  <UserPlusIcon className="w-7 h-7 text-[#00c7be]" />
                </div>
                <h2 className="text-[24px] font-display font-bold text-white mb-2">
                  Dashboard Registration
                </h2>
                <p className="text-white/40 text-[14px]">
                  Initialize your revenue intelligence account
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

                {/* Entity Name */}
                <div className="auth-fade-up-d1">
                  <label
                    htmlFor="signup-name"
                    className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                  >
                    Entity Name
                  </label>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <IdentificationIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                    <input
                      {...register('name')}
                      id="signup-name"
                      type="text"
                      autoComplete="name"
                      placeholder="Your full name"
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                  </div>
                  {errors.name && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.name.message}</p>
                  )}
                </div>

                {/* Work Identity */}
                <div className="auth-fade-up-d1">
                  <label
                    htmlFor="signup-email"
                    className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                  >
                    Work Identity
                  </label>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                    <input
                      {...register('email')}
                      id="signup-email"
                      type="email"
                      autoComplete="email"
                      placeholder="name@company.ai"
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                  </div>
                  {errors.email && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                  )}
                </div>

                {/* Company */}
                <div className="auth-fade-up-d2">
                  <label
                    htmlFor="signup-company"
                    className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                  >
                    Organization
                  </label>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <BuildingOfficeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                    <input
                      {...register('company')}
                      id="signup-company"
                      type="text"
                      autoComplete="organization"
                      placeholder="Company name"
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                  </div>
                  {errors.company && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.company.message}</p>
                  )}
                </div>

                {/* Company Website */}
                <div className="auth-fade-up-d2">
                  <label
                    htmlFor="signup-website"
                    className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                  >
                    Domain
                  </label>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
                    </svg>
                    <input
                      {...register('website')}
                      id="signup-website"
                      type="url"
                      autoComplete="url"
                      placeholder="https://company.com"
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                  </div>
                  {errors.website && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.website.message}</p>
                  )}
                </div>

                {/* Encryption Key */}
                <div className="auth-fade-up-d2">
                  <label
                    htmlFor="signup-password"
                    className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                  >
                    Encryption Key
                  </label>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                    <input
                      {...register('password')}
                      id="signup-password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      placeholder="Create a strong password"
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-11 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeSlashIcon className="w-[18px] h-[18px]" />
                      ) : (
                        <EyeIcon className="w-[18px] h-[18px]" />
                      )}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.password.message}</p>
                  )}
                </div>

                {/* Terms Checkbox — BUG-005: now validated via Zod schema */}
                <div className="flex items-start gap-2.5 py-1 auth-fade-up-d3">
                  <input
                    type="checkbox"
                    id="terms"
                    checked={!!termsAccepted}
                    onChange={(e) => setValue('termsAccepted', e.target.checked as unknown as true, { shouldValidate: true })}
                    className="mt-0.5 w-4 h-4 rounded border-white/10 bg-white/5 text-[#00c7be] focus:ring-[#00c7be] focus:ring-offset-black cursor-pointer"
                    aria-invalid={!!errors.termsAccepted}
                    aria-describedby={errors.termsAccepted ? 'terms-error' : undefined}
                  />
                  <label
                    htmlFor="terms"
                    className="text-[12px] text-white/40 font-medium leading-relaxed cursor-pointer select-none"
                  >
                    I agree to the{' '}
                    <a href="/terms" className="text-[#00c7be] hover:underline">
                      Terms of Service
                    </a>{' '}
                    and{' '}
                    <a href="/privacy" className="text-[#00c7be] hover:underline">
                      Privacy Policy
                    </a>
                    .
                  </label>
                </div>
                {errors.termsAccepted && (
                  <p id="terms-error" className="text-xs text-red-400 -mt-2 ml-1">
                    {errors.termsAccepted.message}
                  </p>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="auth-fade-up-d3 w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[44px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-1 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Creating account...
                    </span>
                  ) : (
                    <>
                      Create account
                      <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                      </svg>
                    </>
                  )}
                </button>
              </form>

              {/* Secure Provisioning Divider */}
              <div className="relative my-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-bold">
                  <span className="bg-black px-4 text-white/20">
                    Secure Provisioning
                  </span>
                </div>
              </div>

              {/* Bottom Link */}
              <div className="text-center">
                <p className="text-[13px] text-white/30">
                  Already have an identity?{' '}
                  <Link
                    to="/login"
                    className="text-[#00c7be] font-bold hover:underline"
                  >
                    System Access
                  </Link>
                </p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
