/**
 * Signup Page - Stratum HoloGlass Theme
 * Deep black background (#0b1215) + gold accent frosted glass cards
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  BuildingOfficeIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { useSignup } from '@/api/auth';
import { pageSEO, SEO } from '@/components/common/SEO';

// Stratum Theme v4.0 - Trust-Gated Autopilot (Landing Page Colors)
const theme = {
  primary: '#00c7be', // Stratum Cyan (matching landing)
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  primaryBright: '#14F0C6',
  orange: '#FF6B35', // Orange Accent
  green: '#34c759', // Status Success
  purple: '#8b5cf6', // Accent Purple
  gold: '#F4D03F', // Gold Accent
  bgVoid: '#050508', // Deepest background
  bgBase: '#0a0a0f', // Deep navy black
  bgCard: 'rgba(18, 18, 26, 0.9)', // Card background
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.06)',
  borderHover: 'rgba(255, 255, 255, 0.10)',
  borderCyan: 'rgba(0, 199, 190, 0.2)',
  success: '#34c759',
  cyanGlow: 'rgba(0, 199, 190, 0.5)',
  cyanSubtle: 'rgba(0, 199, 190, 0.1)',
};

// HUD Corner component for sci-fi styling
const HUDCorner = ({ position }: { position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' }) => {
  const styles: Record<string, React.CSSProperties> = {
    'top-left': { top: 20, left: 20, borderRight: 'none', borderBottom: 'none' },
    'top-right': { top: 20, right: 20, borderLeft: 'none', borderBottom: 'none' },
    'bottom-left': { bottom: 20, left: 20, borderRight: 'none', borderTop: 'none' },
    'bottom-right': { bottom: 20, right: 20, borderLeft: 'none', borderTop: 'none' },
  };
  return (
    <div
      className="hidden lg:block fixed pointer-events-none"
      style={{
        width: 60,
        height: 60,
        border: `2px solid ${theme.primary}`,
        opacity: 0.4,
        zIndex: 1,
        ...styles[position],
      }}
    />
  );
};

const signupSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email'),
    company: z.string().min(2, 'Company name is required'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type SignupForm = z.infer<typeof signupSchema>;

export default function Signup() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

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
      },
      {
        onSuccess: () => {
          navigate('/login', { state: { registered: true } });
        },
      }
    );
  };

  return (
    <div className="min-h-screen flex" style={{ background: theme.bgVoid }}>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />

      {/* HUD Corners */}
      <HUDCorner position="top-left" />
      <HUDCorner position="top-right" />
      <HUDCorner position="bottom-left" />
      <HUDCorner position="bottom-right" />

      {/* Ambient orbs background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 40% 40% at 20% 30%, ${theme.cyanSubtle}, transparent),
            radial-gradient(ellipse 30% 30% at 80% 70%, rgba(255, 107, 53, 0.06), transparent),
            radial-gradient(ellipse 35% 35% at 60% 20%, rgba(0, 199, 190, 0.08), transparent)
          `,
        }}
      />

      {/* LEFT PANEL - BRANDING */}
      <div className="hidden lg:flex lg:w-1/2 relative" style={{ background: theme.bgVoid }}>
        <div className="absolute inset-y-0 right-0 w-px" style={{ background: theme.border }} />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div>
            <Link to="/" className="flex items-center gap-3 mb-16 group">
              <div
                className="h-10 w-10 rounded-2xl flex items-center justify-center transition-all duration-300 group-hover:scale-105"
                style={{ background: theme.primary }}
              >
                <span className="text-white font-semibold text-lg">S</span>
              </div>
              <div>
                <span
                  className="text-xl font-semibold tracking-tight"
                  style={{ color: theme.textPrimary }}
                >
                  Stratum AI
                </span>
                <div
                  className="text-xs tracking-widest uppercase"
                  style={{ color: theme.primary }}
                >
                  Revenue OS
                </div>
              </div>
            </Link>

            <h1
              className="text-4xl font-semibold mb-4 leading-tight"
              style={{ color: theme.textPrimary, letterSpacing: '-0.02em' }}
            >
              Start optimizing
              <br />
              your revenue with
              <br />
              <span style={{ color: theme.primary }}>AI-powered</span> insights
            </h1>
            <p className="text-lg max-w-md leading-relaxed" style={{ color: theme.textMuted }}>
              Join 150+ growth teams using Stratum to automate marketing decisions and recover lost
              revenue.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-4">
              {[
                { icon: '✓', text: '14-day free trial' },
                { icon: '✓', text: 'No credit card required' },
                { icon: '✓', text: 'Cancel anytime' },
              ].map((item) => (
                <div
                  key={item.text}
                  className="flex items-center gap-2"
                  style={{ color: theme.textMuted }}
                >
                  <span style={{ color: theme.success }}>{item.icon}</span>
                  <span className="text-sm">{item.text}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6">
            {[
              { value: '150+', label: 'Growth Teams' },
              { value: '$12M+', label: 'Revenue Recovered' },
              { value: '4.2x', label: 'Avg ROAS Lift' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl font-semibold" style={{ color: theme.textPrimary }}>
                  {stat.value}
                </div>
                <div className="text-sm" style={{ color: theme.textMuted }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL - SIGNUP FORM */}
      <div className="flex-1 flex items-center justify-center p-8 relative z-10">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <div
              className="h-10 w-10 rounded-2xl flex items-center justify-center"
              style={{ background: theme.primary }}
            >
              <span className="text-white font-semibold text-lg">S</span>
            </div>
            <span className="text-xl font-semibold" style={{ color: theme.textPrimary }}>
              Stratum AI
            </span>
          </div>

          {/* Card */}
          <div
            className="p-8 rounded-3xl"
            style={{
              background: theme.bgCard,
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
              border: `1px solid ${theme.border}`,
              boxShadow: '0 25px 50px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div className="text-center mb-8">
              <h2 className="text-2xl font-semibold mb-2" style={{ color: theme.textPrimary }}>
                Create your account
              </h2>
              <p style={{ color: theme.textMuted }}>Start your 14-day free trial</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {apiError && (
                <div
                  className="flex items-center gap-3 p-4 rounded-xl text-sm"
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#EF4444',
                  }}
                >
                  <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                  <span>{apiError}</span>
                </div>
              )}

              {/* Name */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    {...register('name')}
                    type="text"
                    placeholder="John Doe"
                    className="w-full pl-12 pr-4 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                </div>
                {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
              </div>

              {/* Email */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  Work Email
                </label>
                <div className="relative">
                  <EnvelopeIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="name@company.com"
                    className="w-full pl-12 pr-4 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                </div>
                {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
              </div>

              {/* Company */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  Company
                </label>
                <div className="relative">
                  <BuildingOfficeIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    {...register('company')}
                    type="text"
                    placeholder="Acme Inc."
                    className="w-full pl-12 pr-4 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                </div>
                {errors.company && <p className="text-sm text-red-500">{errors.company.message}</p>}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  Password
                </label>
                <div className="relative">
                  <LockClosedIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    className="w-full pl-12 pr-12 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                    style={{ color: theme.textMuted }}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeSlashIcon className="w-5 h-5" />
                    ) : (
                      <EyeIcon className="w-5 h-5" />
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-sm text-red-500">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  Confirm Password
                </label>
                <div className="relative">
                  <LockClosedIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    {...register('confirmPassword')}
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Confirm password"
                    className="w-full pl-12 pr-12 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                    style={{ color: theme.textMuted }}
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? (
                      <EyeSlashIcon className="w-5 h-5" />
                    ) : (
                      <EyeIcon className="w-5 h-5" />
                    )}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-sm text-red-500">{errors.confirmPassword.message}</p>
                )}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 rounded-2xl font-semibold text-white transition-all duration-200 disabled:opacity-50 mt-2"
                style={{
                  background: `linear-gradient(135deg, ${theme.primary}, ${theme.primaryBright})`,
                  boxShadow: `0 0 30px ${theme.cyanGlow}`,
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = `0 0 40px ${theme.cyanGlow}`;
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = `0 0 30px ${theme.cyanGlow}`;
                }}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
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
                  'Create account'
                )}
              </button>
            </form>

            {/* Login link */}
            <p className="text-center text-sm mt-6" style={{ color: theme.textMuted }}>
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium transition-colors hover:underline"
                style={{ color: theme.primary }}
              >
                Sign in
              </Link>
            </p>
          </div>

          <p className="text-center text-xs mt-6" style={{ color: theme.textMuted }}>
            By creating an account, you agree to our{' '}
            <a href="#" className="hover:underline" style={{ color: theme.textSecondary }}>
              Terms
            </a>{' '}
            and{' '}
            <a href="#" className="hover:underline" style={{ color: theme.textSecondary }}>
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
