/**
 * Signup Page - Stratum AI
 * Gold/Crimson/Charcoal design: Two-panel layout with ROI calculator + modern form
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
} from '@heroicons/react/24/outline';
import { useSignup } from '@/api/auth';
import { pageSEO, SEO } from '@/components/common/SEO';

// ---------------------------------------------------------------------------
// Zod Schema (unchanged)
// ---------------------------------------------------------------------------
const signupSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email'),
    company: z.string().min(2, 'Company name is required'),
    website: z.string().min(4, 'Company website is required'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type SignupForm = z.infer<typeof signupSchema>;

// ---------------------------------------------------------------------------
// Styles — Gold / Crimson / Charcoal
// ---------------------------------------------------------------------------
const pageStyles = `
  .signup-mesh-bg {
    background-image: radial-gradient(circle at 1px 1px, rgba(184, 134, 11, 0.08) 1px, transparent 0);
    background-size: 40px 40px;
  }
  .signup-hero-gradient {
    background: radial-gradient(circle at 50% -20%, rgba(139, 0, 0, 0.25) 0%, rgba(184, 134, 11, 0.1) 50%, transparent 100%), #1A1A1A;
  }
  .signup-glass {
    background: rgba(20, 20, 20, 0.75);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(184, 134, 11, 0.25);
  }
  .signup-glow-gold {
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
  }
  .signup-glow-gold:hover {
    box-shadow: 0 0 30px rgba(255, 215, 0, 0.45);
  }
  @keyframes signupScroll {
    0% { transform: translateY(0); }
    100% { transform: translateY(-50%); }
  }
  .signup-animate-scroll {
    animation: signupScroll 20s linear infinite;
  }
  .signup-mask-fade-y {
    mask-image: linear-gradient(to bottom, transparent, black 20%, black 80%, transparent);
    -webkit-mask-image: linear-gradient(to bottom, transparent, black 20%, black 80%, transparent);
  }
  .signup-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #FFD700;
    cursor: pointer;
    box-shadow: 0 0 8px rgba(255, 215, 0, 0.5);
  }
  .signup-range::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #FFD700;
    cursor: pointer;
    border: none;
    box-shadow: 0 0 8px rgba(255, 215, 0, 0.5);
  }
  .signup-gradient-text {
    background: linear-gradient(135deg, #FFD700 0%, #DC143C 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
`;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function Signup() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [adSpend, setAdSpend] = useState(25000);

  const registerMutation = useSignup();
  const isLoading = registerMutation.isPending;
  const apiError = registerMutation.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
  });

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
        onSuccess: () => {
          navigate('/login', { state: { registered: true } });
        },
      }
    );
  };

  // ROI Calculator derived values
  const projectedRecovery = Math.round(adSpend * 0.17);
  const efficiencyLift = ((projectedRecovery / adSpend) * 100).toFixed(1);

  return (
    <>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />
      <style>{pageStyles}</style>

      <div className="bg-[#1A1A1A] text-[#F5F5F0] min-h-screen flex font-sans selection:bg-[#FFD700]/30">
        {/* Mesh dot grid background */}
        <div className="fixed inset-0 signup-mesh-bg pointer-events-none opacity-40" />
        {/* Ambient glow orbs */}
        <div className="fixed top-0 right-0 w-[800px] h-[800px] bg-[#8B0000]/5 rounded-full blur-[150px] pointer-events-none" />
        <div className="fixed bottom-0 left-0 w-[800px] h-[800px] bg-[#B8860B]/5 rounded-full blur-[150px] pointer-events-none" />

        <main className="relative z-10 w-full flex flex-col lg:flex-row min-h-screen">
          {/* ================================================================
              LEFT PANEL - BRANDING + ROI CALCULATOR
              ================================================================ */}
          <section className="lg:w-7/12 p-6 lg:p-[48px] flex flex-col justify-between space-y-6 hidden lg:flex signup-hero-gradient">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="w-10 h-10 bg-[#FFD700] rounded-lg flex items-center justify-center rotate-45 shadow-[0_0_15px_rgba(255,215,0,0.3)]">
                <span className="font-display font-bold text-[#1A1A1A] text-xl -rotate-45">S</span>
              </div>
              <div>
                <h1 className="font-display font-bold text-lg leading-tight tracking-tight">STRATUM AI</h1>
                <p className="text-[10px] tracking-widest text-[#FFD700] font-bold uppercase">
                  Revenue OS
                </p>
              </div>
            </Link>

            {/* Hero heading */}
            <div className="max-w-xl">
              <h2 className="text-3xl lg:text-5xl font-display font-extrabold leading-tight mb-4">
                Start optimizing your revenue with{' '}
                <span className="signup-gradient-text italic">AI-powered</span> insights
              </h2>
              <p className="text-[#F5F5F0]/50 text-lg leading-relaxed">
                Join 150+ growth teams using Stratum to automate marketing decisions and recover lost
                revenue through predictive analytics.
              </p>
            </div>

            {/* ROI Calculator Card */}
            <div className="max-w-md signup-glass p-5 rounded-2xl shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-display font-bold text-lg flex items-center gap-2">
                  <svg
                    className="w-5 h-5 text-[#FFD700]"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                    />
                  </svg>
                  Live ROI Calculator
                </h3>
                <span className="px-2 py-1 bg-[#FFD700]/10 text-[#FFD700] text-[10px] font-bold rounded-full uppercase tracking-wider">
                  Predictive
                </span>
              </div>

              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2 font-medium">
                    <label className="text-[#F5F5F0]/50">Monthly Ad Spend</label>
                    <span className="text-[#FFD700] font-mono font-bold">
                      ${adSpend.toLocaleString()}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1000"
                    max="100000"
                    step="1000"
                    value={adSpend}
                    onChange={(e) => setAdSpend(Number(e.target.value))}
                    className="signup-range w-full h-1.5 bg-black/40 rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[#B8860B]/20">
                  <div>
                    <p className="text-[11px] text-[#F5F5F0]/40 uppercase font-bold tracking-wider mb-1">
                      Projected Recovery
                    </p>
                    <p className="text-2xl font-display font-bold text-[#FFD700]">
                      +${projectedRecovery.toLocaleString()}
                      <span className="text-xs font-normal text-[#F5F5F0]/40 ml-1">/mo</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-[#F5F5F0]/40 uppercase font-bold tracking-wider mb-1">
                      Efficiency Lift
                    </p>
                    <p className="text-2xl font-display font-bold text-[#F5F5F0]">{efficiencyLift}%</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Trust badges + Social proof */}
            <div className="space-y-5">
              <div className="flex flex-wrap gap-5 text-sm text-[#F5F5F0]/50 font-medium">
                {['14-day free trial', 'No credit card required', 'Cancel anytime'].map((text) => (
                  <div key={text} className="flex items-center gap-2">
                    <svg
                      className="w-4 h-4 text-[#FFD700]"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                    </svg>
                    {text}
                  </div>
                ))}
              </div>

              {/* Scrolling social proof */}
              <div className="relative overflow-hidden h-12 signup-mask-fade-y">
                <div className="signup-animate-scroll space-y-4">
                  {[
                    { company: 'ShopSphere', text: 'recovered $12k in churned revenue today' },
                    { company: 'Vertex Ltd', text: 'increased ROAS by 22% this week' },
                    { company: 'Aura Analytics', text: 'scaled spend by 3x with Stratum' },
                    { company: 'ShopSphere', text: 'recovered $12k in churned revenue today' },
                    { company: 'Vertex Ltd', text: 'increased ROAS by 22% this week' },
                    { company: 'Aura Analytics', text: 'scaled spend by 3x with Stratum' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm text-[#F5F5F0]/50">
                      <div className="w-1.5 h-1.5 bg-[#FFD700] rounded-full animate-pulse" />
                      <span className="font-bold text-[#F5F5F0]/80">{item.company}</span> {item.text}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ================================================================
              RIGHT PANEL - SIGNUP FORM
              ================================================================ */}
          <section className="lg:w-5/12 p-4 lg:p-[40px] flex items-center justify-center bg-black/20 min-h-screen">
            <div className="w-full max-w-md">
              {/* Mobile logo */}
              <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
                <div className="w-10 h-10 bg-[#FFD700] rounded-lg flex items-center justify-center rotate-45 shadow-[0_0_15px_rgba(255,215,0,0.3)]">
                  <span className="font-display font-bold text-[#1A1A1A] text-xl -rotate-45">S</span>
                </div>
                <span className="font-display font-bold text-xl tracking-tight">STRATUM AI</span>
              </div>

              {/* Form Card */}
              <div className="signup-glass p-5 lg:p-[28px] rounded-[1.5rem] shadow-2xl">
                <div className="text-center mb-5">
                  <h2 className="text-xl lg:text-2xl font-display font-bold mb-1">
                    Create your account
                  </h2>
                  <p className="text-[#F5F5F0]/50 text-sm">Start your 14-day free trial</p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                  {apiError && (
                    <div className="flex items-center gap-3 p-4 rounded-xl text-sm bg-[#DC143C]/10 border border-[#DC143C]/30 text-[#DC143C]">
                      <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                      <span>{apiError}</span>
                    </div>
                  )}

                  {/* Full Name */}
                  <div>
                    <label
                      htmlFor="signup-name"
                      className="block text-xs font-bold text-[#F5F5F0]/50 uppercase tracking-wider mb-2 ml-1"
                    >
                      Full Name
                    </label>
                    <input
                      {...register('name')}
                      id="signup-name"
                      type="text"
                      placeholder="John Doe"
                      className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700] focus:ring-0 rounded-xl px-4 py-2.5 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                    />
                    {errors.name && (
                      <p className="text-xs text-[#DC143C] mt-1 ml-1">{errors.name.message}</p>
                    )}
                  </div>

                  {/* Work Email */}
                  <div>
                    <label
                      htmlFor="signup-email"
                      className="block text-xs font-bold text-[#F5F5F0]/50 uppercase tracking-wider mb-2 ml-1"
                    >
                      Work Email
                    </label>
                    <div className="relative">
                      <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#F5F5F0]/40" />
                      <input
                        {...register('email')}
                        id="signup-email"
                        type="email"
                        placeholder="name@company.com"
                        className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700] focus:ring-0 rounded-xl pl-12 pr-4 py-2.5 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                      />
                    </div>
                    {errors.email && (
                      <p className="text-xs text-[#DC143C] mt-1 ml-1">{errors.email.message}</p>
                    )}
                  </div>

                  {/* Company */}
                  <div>
                    <label
                      htmlFor="signup-company"
                      className="block text-xs font-bold text-[#F5F5F0]/50 uppercase tracking-wider mb-2 ml-1"
                    >
                      Company
                    </label>
                    <input
                      {...register('company')}
                      id="signup-company"
                      type="text"
                      placeholder="Acme Inc."
                      className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700] focus:ring-0 rounded-xl px-4 py-2.5 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                    />
                    {errors.company && (
                      <p className="text-xs text-[#DC143C] mt-1 ml-1">{errors.company.message}</p>
                    )}
                  </div>

                  {/* Company Website */}
                  <div>
                    <label
                      htmlFor="signup-website"
                      className="block text-xs font-bold text-[#F5F5F0]/50 uppercase tracking-wider mb-2 ml-1"
                    >
                      Company Website
                    </label>
                    <input
                      {...register('website')}
                      id="signup-website"
                      type="url"
                      placeholder="https://example.com"
                      className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700] focus:ring-0 rounded-xl px-4 py-2.5 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                    />
                    {errors.website && (
                      <p className="text-xs text-[#DC143C] mt-1 ml-1">{errors.website.message}</p>
                    )}
                  </div>

                  {/* Password */}
                  <div>
                    <label
                      htmlFor="signup-password"
                      className="block text-xs font-bold text-[#F5F5F0]/50 uppercase tracking-wider mb-2 ml-1"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#F5F5F0]/40" />
                      <input
                        {...register('password')}
                        id="signup-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="••••••••••••"
                        className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700] focus:ring-0 rounded-xl pl-12 pr-12 py-2.5 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                      />
                      <button
                        type="button"
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#F5F5F0]/40 hover:text-[#F5F5F0]/80 transition-colors"
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
                      <p className="text-xs text-[#DC143C] mt-1 ml-1">{errors.password.message}</p>
                    )}
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label
                      htmlFor="signup-confirm"
                      className="block text-xs font-bold text-[#F5F5F0]/50 uppercase tracking-wider mb-2 ml-1"
                    >
                      Confirm Password
                    </label>
                    <div className="relative">
                      <input
                        {...register('confirmPassword')}
                        id="signup-confirm"
                        type={showConfirmPassword ? 'text' : 'password'}
                        placeholder="Confirm password"
                        className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700] focus:ring-0 rounded-xl px-4 pr-12 py-2.5 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                      />
                      <button
                        type="button"
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#F5F5F0]/40 hover:text-[#F5F5F0]/80 transition-colors"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      >
                        {showConfirmPassword ? (
                          <EyeSlashIcon className="w-[18px] h-[18px]" />
                        ) : (
                          <EyeIcon className="w-[18px] h-[18px]" />
                        )}
                      </button>
                    </div>
                    {errors.confirmPassword && (
                      <p className="text-xs text-[#DC143C] mt-1 ml-1">
                        {errors.confirmPassword.message}
                      </p>
                    )}
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-[#FFD700] text-[#1A1A1A] font-bold py-3 rounded-xl shadow-lg signup-glow-gold hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-50 disabled:hover:scale-100"
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                            fill="none"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                        Creating account...
                      </span>
                    ) : (
                      <>
                        Create account
                        <svg
                          className="w-[18px] h-[18px]"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2.5}
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
                          />
                        </svg>
                      </>
                    )}
                  </button>

                  {/* Sign in link */}
                  <p className="text-center text-sm text-[#F5F5F0]/50 mt-5">
                    Already have an account?{' '}
                    <Link
                      to="/login"
                      className="text-[#FFD700] font-bold hover:underline"
                    >
                      Sign in
                    </Link>
                  </p>
                </form>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
