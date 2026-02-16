/**
 * Signup Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card registration form
 * Cyberpunk Dark theme — midnight navy + spectral pink/orange/gold
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
  LockClosedIcon,
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
          <section className="lg:w-5/12 w-full flex flex-col items-center justify-center p-6 lg:p-8 bg-[#0A1628] relative">
            {/* Mobile logo */}
            <div className="lg:hidden absolute top-8 left-8 flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-[#FF1F6D] to-[#FF3D00] rounded-lg flex items-center justify-center rotate-45 shadow-[0_0_15px_rgba(255,31,109,0.4)]">
                <span className="font-display font-bold text-white text-xs -rotate-45">✦</span>
              </div>
              <span className="font-display font-bold text-lg tracking-tighter text-white">
                STRATUM AI
              </span>
            </div>

            <div className="w-full max-w-[448px] flex flex-col items-center">
              <div className="auth-glass-card w-full rounded-xl p-10 space-y-8 relative overflow-hidden auth-fade-up mb-12">
                {/* Decorative glows */}
                <div className="absolute -top-10 -right-10 w-32 h-32 bg-[#00F5FF]/10 rounded-full blur-3xl" style={{ boxShadow: '0 0 15px rgba(0, 245, 255, 0.3)' }} />
                <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-[#FFD700]/10 rounded-full blur-3xl" style={{ boxShadow: '0 0 15px rgba(255, 215, 0, 0.3)' }} />

                {/* Header */}
                <div className="space-y-2">
                  <h2 className="text-2xl font-display font-extrabold tracking-tight text-white uppercase">
                    Dashboard Registration
                  </h2>
                  <p className="text-sm text-slate-400 font-medium">
                    Provision your secure workspace
                  </p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                  {/* API Error Alert */}
                  {apiError && (
                    <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400">
                      <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                      <span>{apiError}</span>
                    </div>
                  )}

                  {/* Full Name */}
                  <div className="space-y-2 auth-fade-up-d1">
                    <label
                      htmlFor="signup-name"
                      className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1"
                    >
                      Full Name
                    </label>
                    <div className="relative">
                      <input
                        {...register('name')}
                        id="signup-name"
                        type="text"
                        autoComplete="name"
                        placeholder="John Doe"
                        className="w-full h-[44px] px-4 rounded-[12px] text-white placeholder:text-slate-600 focus:ring-0 bg-[rgba(5,11,24,0.6)] border border-white/10 transition-all focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.2)] outline-none text-[14px]"
                      />
                      <svg className="absolute right-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                      </svg>
                    </div>
                    {errors.name && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.name.message}</p>
                    )}
                  </div>

                  {/* Work Identity */}
                  <div className="space-y-2 auth-fade-up-d1">
                    <label
                      htmlFor="signup-email"
                      className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1"
                    >
                      Work Identity
                    </label>
                    <div className="relative">
                      <input
                        {...register('email')}
                        id="signup-email"
                        type="email"
                        autoComplete="email"
                        placeholder="name@company.ai"
                        className="w-full h-[44px] px-4 rounded-[12px] text-white placeholder:text-slate-600 focus:ring-0 bg-[rgba(5,11,24,0.6)] border border-white/10 transition-all focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.2)] outline-none text-[14px]"
                      />
                      <EnvelopeIcon className="absolute right-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600" />
                    </div>
                    {errors.email && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                    )}
                  </div>

                  {/* Organization */}
                  <div className="space-y-2 auth-fade-up-d2">
                    <label
                      htmlFor="signup-company"
                      className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1"
                    >
                      Organization
                    </label>
                    <div className="relative">
                      <input
                        {...register('company')}
                        id="signup-company"
                        type="text"
                        autoComplete="organization"
                        placeholder="Company name"
                        className="w-full h-[44px] px-4 rounded-[12px] text-white placeholder:text-slate-600 focus:ring-0 bg-[rgba(5,11,24,0.6)] border border-white/10 transition-all focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.2)] outline-none text-[14px]"
                      />
                      <BuildingOfficeIcon className="absolute right-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600" />
                    </div>
                    {errors.company && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.company.message}</p>
                    )}
                  </div>

                  {/* Domain / Website */}
                  <div className="space-y-2 auth-fade-up-d2">
                    <label
                      htmlFor="signup-website"
                      className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1"
                    >
                      Domain
                    </label>
                    <div className="relative">
                      <input
                        {...register('website')}
                        id="signup-website"
                        type="url"
                        autoComplete="url"
                        placeholder="https://company.com"
                        className="w-full h-[44px] px-4 rounded-[12px] text-white placeholder:text-slate-600 focus:ring-0 bg-[rgba(5,11,24,0.6)] border border-white/10 transition-all focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.2)] outline-none text-[14px]"
                      />
                      <svg className="absolute right-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
                      </svg>
                    </div>
                    {errors.website && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.website.message}</p>
                    )}
                  </div>

                  {/* Encryption Key */}
                  <div className="space-y-2 auth-fade-up-d2">
                    <label
                      htmlFor="signup-password"
                      className="text-[10px] font-bold uppercase tracking-widest text-slate-500 ml-1"
                    >
                      Encryption Key
                    </label>
                    <div className="relative">
                      <input
                        {...register('password')}
                        id="signup-password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        placeholder="••••••••••••"
                        className="w-full h-[44px] px-4 pr-11 rounded-[12px] text-white placeholder:text-slate-600 focus:ring-0 bg-[rgba(5,11,24,0.6)] border border-white/10 transition-all focus:border-[#FF8C00] focus:shadow-[0_0_15px_rgba(255,140,0,0.2)] outline-none text-[14px] font-mono"
                      />
                      <button
                        type="button"
                        tabIndex={-1}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-600 hover:text-white/60 transition-colors"
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
                      className="mt-0.5 w-4 h-4 rounded border-white/10 bg-white/5 text-[#FF1F6D] focus:ring-[#FF1F6D] focus:ring-offset-[#0A1628] cursor-pointer"
                      aria-invalid={!!errors.termsAccepted}
                      aria-describedby={errors.termsAccepted ? 'terms-error' : undefined}
                    />
                    <label
                      htmlFor="terms"
                      className="text-[11px] text-slate-400 font-medium leading-relaxed cursor-pointer select-none"
                    >
                      I agree to the{' '}
                      <a href="/terms" className="text-[#FF1F6D] hover:underline">
                        Terms of Service
                      </a>{' '}
                      and{' '}
                      <a href="/privacy" className="text-[#FF1F6D] hover:underline">
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
                  <div className="pt-4">
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="auth-fade-up-d3 w-full h-[56px] rounded-xl font-black text-sm tracking-[0.2em] uppercase transition-all duration-300 auth-gradient-btn auth-shimmer-btn text-white flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:scale-100 hover:translate-y-[-1px]"
                    >
                      {isLoading ? (
                        <span className="flex items-center gap-2">
                          <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Initializing...
                        </span>
                      ) : (
                        'Initialize Account'
                      )}
                    </button>
                  </div>
                </form>

                {/* Or connect via divider */}
                <div className="flex items-center gap-4 py-2">
                  <div className="h-px bg-white/5 flex-grow" />
                  <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">or connect via</span>
                  <div className="h-px bg-white/5 flex-grow" />
                </div>

                {/* OAuth Buttons */}
                <div className="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    className="flex items-center justify-center gap-2 h-[44px] rounded-[12px] border border-white/5 bg-white/5 hover:bg-white/10 transition-colors text-xs font-bold text-slate-300"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.48 10.92v3.28h7.84c-.24 1.84-.909 3.292-2.09 4.458-1.488 1.489-3.391 2.454-6.09 2.454-4.591 0-8.203-3.666-8.203-8.203s3.612-8.203 8.203-8.203c2.49 0 4.408.981 5.845 2.371l2.307-2.307C18.183 2.503 15.588 1 12.48 1 6.302 1 1.29 6.012 1.29 12.19s5.012 11.19 11.19 11.19c3.3 0 5.803-1.082 7.79-3.15 2.011-2.011 2.651-4.852 2.651-7.151 0-.68-.06-1.32-.18-1.89h-10.27z" /></svg>
                    Google
                  </button>
                  <button
                    type="button"
                    className="flex items-center justify-center gap-2 h-[44px] rounded-[12px] border border-white/5 bg-white/5 hover:bg-white/10 transition-colors text-xs font-bold text-slate-300"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.042-1.416-4.042-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" /></svg>
                    GitHub
                  </button>
                </div>

                {/* Already authenticated link */}
                <p className="text-[10px] text-center text-slate-500 uppercase tracking-widest font-medium">
                  Already authenticated?{' '}
                  <Link
                    to="/login"
                    className="text-[#FF1F6D] hover:text-[#FF3D00] transition-colors"
                  >
                    Resume Session
                  </Link>
                </p>
              </div>

              {/* Structural divider */}
              <div className="w-full h-px mb-8" style={{ background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent)' }} />

              {/* Status indicators */}
              <div className="flex gap-10 items-center justify-center">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00F5FF] animate-pulse" style={{ boxShadow: '0 0 15px rgba(0, 245, 255, 0.3)' }} />
                  <span className="text-[9px] font-mono text-slate-400 uppercase tracking-tighter">API: Stable</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FFD700]" style={{ boxShadow: '0 0 15px rgba(255, 215, 0, 0.3)' }} />
                  <span className="text-[9px] font-mono text-slate-400 uppercase tracking-tighter">Latency: 24ms</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-mono text-slate-600 uppercase tracking-tighter">v2.026.04.12</span>
                </div>
              </div>
            </div>

            {/* Footer links */}
            <div className="absolute bottom-6 flex gap-6 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              <a href="/privacy" className="hover:text-white transition-colors">Privacy Protocol</a>
              <a href="/terms" className="hover:text-white transition-colors">Service Terms</a>
              <a href="/support" className="hover:text-white transition-colors">Help Terminal</a>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
