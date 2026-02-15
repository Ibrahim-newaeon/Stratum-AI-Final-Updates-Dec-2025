/**
 * Signup Page - Stratum AI
 * New design: Two-panel layout with ROI calculator + modern form
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
// Styles (injected via <style> tag)
// ---------------------------------------------------------------------------
const pageStyles = `
  .signup-dot-grid {
    background-image: radial-gradient(circle at 2px 2px, rgba(0, 229, 193, 0.05) 1px, transparent 0);
    background-size: 40px 40px;
  }
  .signup-glow-primary {
    box-shadow: 0 0 20px rgba(0, 229, 193, 0.3);
  }
  .signup-glow-primary:hover {
    box-shadow: 0 0 30px rgba(0, 229, 193, 0.45);
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
    background: #00E5C1;
    cursor: pointer;
    box-shadow: 0 0 8px rgba(0, 229, 193, 0.5);
  }
  .signup-range::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #00E5C1;
    cursor: pointer;
    border: none;
    box-shadow: 0 0 8px rgba(0, 229, 193, 0.5);
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

      <div className="bg-[#020617] text-slate-100 min-h-screen flex font-sans selection:bg-[#00E5C1]/30">
        {/* Dot grid background */}
        <div className="fixed inset-0 signup-dot-grid pointer-events-none opacity-20" />

        <main className="relative z-10 w-full flex flex-col lg:flex-row min-h-screen">
          {/* ================================================================
              LEFT PANEL - BRANDING + ROI CALCULATOR
              ================================================================ */}
          <section className="lg:w-7/12 p-8 lg:p-16 flex flex-col justify-between space-y-12 hidden lg:flex">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="w-10 h-10 bg-[#00E5C1] rounded-lg flex items-center justify-center">
                <span className="font-display font-bold text-[#020617] text-xl">S</span>
              </div>
              <div>
                <h1 className="font-display font-bold text-lg leading-tight">Stratum AI</h1>
                <p className="text-[10px] tracking-widest text-[#00E5C1] font-bold uppercase">
                  Revenue OS
                </p>
              </div>
            </Link>

            {/* Hero heading */}
            <div className="max-w-xl">
              <h2 className="text-4xl lg:text-6xl font-display font-bold leading-tight mb-6">
                Start optimizing your revenue with{' '}
                <span className="text-[#00E5C1] italic">AI-powered</span> insights
              </h2>
              <p className="text-slate-400 text-lg leading-relaxed">
                Join 150+ growth teams using Stratum to automate marketing decisions and recover lost
                revenue through predictive analytics.
              </p>
            </div>

            {/* ROI Calculator Card */}
            <div className="max-w-md bg-white/5 backdrop-blur-md border border-slate-700/50 p-6 rounded-2xl shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-display font-bold text-lg flex items-center gap-2">
                  <svg
                    className="w-5 h-5 text-[#00E5C1]"
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
                <span className="px-2 py-1 bg-[#00E5C1]/10 text-[#00E5C1] text-[10px] font-bold rounded-full uppercase tracking-wider">
                  Predictive
                </span>
              </div>

              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2 font-medium">
                    <label className="text-slate-400">Monthly Ad Spend</label>
                    <span className="text-[#00E5C1]">
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
                    className="signup-range w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700/50">
                  <div>
                    <p className="text-[11px] text-slate-400 uppercase font-bold tracking-wider mb-1">
                      Projected Recovery
                    </p>
                    <p className="text-2xl font-display font-bold text-[#00E5C1]">
                      +${projectedRecovery.toLocaleString()}
                      <span className="text-xs font-normal text-slate-400 ml-1">/mo</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-400 uppercase font-bold tracking-wider mb-1">
                      Efficiency Lift
                    </p>
                    <p className="text-2xl font-display font-bold text-white">{efficiencyLift}%</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Trust badges + Social proof */}
            <div className="space-y-8">
              <div className="flex flex-wrap gap-6 text-sm text-slate-400 font-medium">
                {['14-day free trial', 'No credit card required', 'Cancel anytime'].map((text) => (
                  <div key={text} className="flex items-center gap-2">
                    <svg
                      className="w-4 h-4 text-[#00E5C1]"
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
                    <div key={i} className="flex items-center gap-3 text-sm text-slate-400">
                      <div className="w-1.5 h-1.5 bg-[#00E5C1] rounded-full animate-pulse" />
                      <span className="font-bold text-slate-200">{item.company}</span> {item.text}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ================================================================
              RIGHT PANEL - SIGNUP FORM
              ================================================================ */}
          <section className="lg:w-5/12 p-6 lg:p-12 flex items-center justify-center bg-slate-900/30 min-h-screen">
            <div className="w-full max-w-md">
              {/* Mobile logo */}
              <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
                <div className="w-10 h-10 bg-[#00E5C1] rounded-lg flex items-center justify-center">
                  <span className="font-display font-bold text-[#020617] text-xl">S</span>
                </div>
                <span className="font-display font-bold text-xl">Stratum AI</span>
              </div>

              {/* Form Card */}
              <div className="bg-[#0f172a] p-8 lg:p-10 rounded-[2rem] border border-slate-800 shadow-2xl">
                <div className="text-center mb-10">
                  <h2 className="text-2xl lg:text-3xl font-display font-bold mb-2">
                    Create your account
                  </h2>
                  <p className="text-slate-400 text-sm">Start your 14-day free trial</p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                  {apiError && (
                    <div className="flex items-center gap-3 p-4 rounded-xl text-sm bg-red-500/10 border border-red-500/30 text-red-400">
                      <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                      <span>{apiError}</span>
                    </div>
                  )}

                  {/* Full Name */}
                  <div>
                    <label
                      htmlFor="signup-name"
                      className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1"
                    >
                      Full Name
                    </label>
                    <input
                      {...register('name')}
                      id="signup-name"
                      type="text"
                      placeholder="John Doe"
                      className="w-full bg-slate-800/50 border border-transparent focus:border-[#00E5C1] focus:ring-0 rounded-xl px-4 py-3.5 text-sm transition-all outline-none text-white placeholder:text-slate-500"
                    />
                    {errors.name && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.name.message}</p>
                    )}
                  </div>

                  {/* Work Email */}
                  <div>
                    <label
                      htmlFor="signup-email"
                      className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1"
                    >
                      Work Email
                    </label>
                    <div className="relative">
                      <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500" />
                      <input
                        {...register('email')}
                        id="signup-email"
                        type="email"
                        placeholder="name@company.com"
                        className="w-full bg-slate-800/50 border border-transparent focus:border-[#00E5C1] focus:ring-0 rounded-xl pl-12 pr-4 py-3.5 text-sm transition-all outline-none text-white placeholder:text-slate-500"
                      />
                    </div>
                    {errors.email && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                    )}
                  </div>

                  {/* Company */}
                  <div>
                    <label
                      htmlFor="signup-company"
                      className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1"
                    >
                      Company
                    </label>
                    <input
                      {...register('company')}
                      id="signup-company"
                      type="text"
                      placeholder="Acme Inc."
                      className="w-full bg-slate-800/50 border border-transparent focus:border-[#00E5C1] focus:ring-0 rounded-xl px-4 py-3.5 text-sm transition-all outline-none text-white placeholder:text-slate-500"
                    />
                    {errors.company && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.company.message}</p>
                    )}
                  </div>

                  {/* Company Website */}
                  <div>
                    <label
                      htmlFor="signup-website"
                      className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1"
                    >
                      Company Website
                    </label>
                    <input
                      {...register('website')}
                      id="signup-website"
                      type="url"
                      placeholder="https://example.com"
                      className="w-full bg-slate-800/50 border border-transparent focus:border-[#00E5C1] focus:ring-0 rounded-xl px-4 py-3.5 text-sm transition-all outline-none text-white placeholder:text-slate-500"
                    />
                    {errors.website && (
                      <p className="text-xs text-red-400 mt-1 ml-1">{errors.website.message}</p>
                    )}
                  </div>

                  {/* Password */}
                  <div>
                    <label
                      htmlFor="signup-password"
                      className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500" />
                      <input
                        {...register('password')}
                        id="signup-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="••••••••••••"
                        className="w-full bg-slate-800/50 border border-transparent focus:border-[#00E5C1] focus:ring-0 rounded-xl pl-12 pr-12 py-3.5 text-sm transition-all outline-none text-white placeholder:text-slate-500"
                      />
                      <button
                        type="button"
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
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

                  {/* Confirm Password */}
                  <div>
                    <label
                      htmlFor="signup-confirm"
                      className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1"
                    >
                      Confirm Password
                    </label>
                    <div className="relative">
                      <input
                        {...register('confirmPassword')}
                        id="signup-confirm"
                        type={showConfirmPassword ? 'text' : 'password'}
                        placeholder="Confirm password"
                        className="w-full bg-slate-800/50 border border-transparent focus:border-[#00E5C1] focus:ring-0 rounded-xl px-4 pr-12 py-3.5 text-sm transition-all outline-none text-white placeholder:text-slate-500"
                      />
                      <button
                        type="button"
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
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
                      <p className="text-xs text-red-400 mt-1 ml-1">
                        {errors.confirmPassword.message}
                      </p>
                    )}
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-[#00E5C1] text-[#020617] font-bold py-4 rounded-xl shadow-lg signup-glow-primary hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-50 disabled:hover:scale-100"
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
                  <p className="text-center text-sm text-slate-400 mt-8">
                    Already have an account?{' '}
                    <Link
                      to="/login"
                      className="text-[#00E5C1] font-bold hover:underline"
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
