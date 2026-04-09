/**
 * Signup Page - Stratum AI
 * Split-screen layout: Trust Gauge left panel + glass card form
 * Cyberpunk Dark theme — midnight navy + spectral pink/orange/gold
 * Matches Login page design language
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  EyeIcon,
  EyeSlashIcon,
  EnvelopeIcon,
  LockClosedIcon,
  UserIcon,
  PhoneIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useSignup, useSendWhatsAppOTP, useVerifyWhatsAppOTP } from '@/api/auth';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

const signupSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email'),
  phone: z.string().min(10, 'Please enter a valid phone number with country code'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  acceptTerms: z.boolean().refine(val => val === true, 'You must accept the terms'),
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type SignupForm = z.infer<typeof signupSchema>;

type SignupStep = 'details' | 'verify-phone' | 'success';

export default function Signup() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [_submittedEmail, setSubmittedEmail] = useState('');
  const [step, setStep] = useState<SignupStep>('details');
  const [formData, setFormData] = useState<SignupForm | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [otpError, setOtpError] = useState('');
  const [otpCountdown, setOtpCountdown] = useState(0);

  const signupMutation = useSignup();
  const sendOTPMutation = useSendWhatsAppOTP();
  const verifyOTPMutation = useVerifyWhatsAppOTP();

  const isLoading = signupMutation.isPending || sendOTPMutation.isPending;
  const isSuccess = signupMutation.isSuccess;
  const apiError = signupMutation.error?.message || sendOTPMutation.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
  });

  // Start countdown timer for OTP resend
  const startOTPCountdown = () => {
    setOtpCountdown(60);
    const timer = setInterval(() => {
      setOtpCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const onSubmit = async (data: SignupForm) => {
    setFormData(data);
    setSubmittedEmail(data.email);

    // Send WhatsApp OTP
    sendOTPMutation.mutate(
      { phone_number: data.phone },
      {
        onSuccess: () => {
          setStep('verify-phone');
          startOTPCountdown();
        },
      }
    );
  };

  const handleVerifyOTP = async () => {
    if (!formData || otpCode.length !== 6) {
      setOtpError('Please enter a valid 6-digit code');
      return;
    }

    setOtpError('');

    verifyOTPMutation.mutate(
      { phone_number: formData.phone, otp_code: otpCode },
      {
        onSuccess: (response) => {
          // OTP verified, now complete registration
          const token = response.verification_token || '';

          signupMutation.mutate({
            full_name: formData.name,
            email: formData.email,
            password: formData.password,
            phone: formData.phone,
            company_website: '',
            verification_token: token,
          });
        },
        onError: (error) => {
          setOtpError(error.message || 'Invalid OTP code');
        },
      }
    );
  };

  const handleResendOTP = () => {
    if (formData && otpCountdown === 0) {
      sendOTPMutation.mutate(
        { phone_number: formData.phone },
        {
          onSuccess: () => {
            startOTPCountdown();
            setOtpCode('');
            setOtpError('');
          },
        }
      );
    }
  };

  // OTP Verification Step
  if (step === 'verify-phone') {
    return (
      <>
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          {/* Background mesh */}
          <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
            <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
          </div>

          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up">
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-full bg-[#FF8C00]/10 border border-[#FF8C00]/20 flex items-center justify-center mx-auto mb-6">
                  <PhoneIcon className="w-8 h-8 text-[#FF8C00]" />
                </div>
                <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                  Verify Signal Channel
                </h2>
                <p className="text-slate-400 text-sm mb-1">
                  We've transmitted a 6-digit code to your WhatsApp
                </p>
                <p className="text-[#FF8C00] font-mono text-sm font-bold">
                  {formData?.phone}
                </p>
              </div>

              {/* OTP Input */}
              <div className="mb-6 auth-fade-up-d1">
                <input
                  type="text"
                  value={otpCode}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                    setOtpCode(value);
                    setOtpError('');
                  }}
                  placeholder="000000"
                  className="w-full text-center text-2xl tracking-[0.5em] h-14 rounded-xl bg-[#050B18]/80 border border-white/10 text-white placeholder:text-slate-600 focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.3)] transition-all outline-none font-mono"
                  maxLength={6}
                />
                {otpError && (
                  <p className="mt-2 text-xs text-red-400 text-center">{otpError}</p>
                )}
              </div>

              <div className="space-y-4 auth-fade-up-d2">
                <button
                  onClick={handleVerifyOTP}
                  disabled={verifyOTPMutation.isPending || otpCode.length !== 6}
                  className="w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {verifyOTPMutation.isPending ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      VERIFYING...
                    </span>
                  ) : (
                    'VERIFY & ACTIVATE'
                  )}
                </button>

                <div className="flex justify-center">
                  <button
                    onClick={handleResendOTP}
                    disabled={otpCountdown > 0 || sendOTPMutation.isPending}
                    className="text-xs text-[#FF1F6D] hover:text-white transition-colors disabled:opacity-40 disabled:hover:text-[#FF1F6D] font-bold uppercase tracking-widest"
                  >
                    {sendOTPMutation.isPending ? (
                      'Transmitting...'
                    ) : otpCountdown > 0 ? (
                      `Retransmit in ${otpCountdown}s`
                    ) : (
                      'Retransmit Code'
                    )}
                  </button>
                </div>

                <div className="flex justify-center">
                  <button
                    onClick={() => setStep('details')}
                    className="text-xs text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono"
                  >
                    &larr; Back to registration
                  </button>
                </div>
              </div>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Success Step
  if (isSuccess) {
    return (
      <>
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          {/* Background mesh */}
          <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
            <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 215, 0, 0.05), transparent 60%)' }} />
          </div>

          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircleIcon className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                Entity Activated
              </h2>
              <p className="text-slate-400 text-sm mb-8">
                Your neural profile has been created. Initialize your session to access Stratum AI.
              </p>
              <button
                onClick={() => navigate('/login', { state: { registered: true } })}
                className="w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98]"
              >
                INITIALIZE SESSION
              </button>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Main Signup Form
  return (
    <>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />
      <style>{authStyles}</style>

      <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
        {/* Background mesh */}
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
          <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 215, 0, 0.05), transparent 60%)' }} />
        </div>

        <main className="relative z-10 w-full flex min-h-screen mx-auto" style={{ maxWidth: '1500px' }}>
          {/* Left Panel — hidden on mobile */}
          <AuthLeftPanel className="hidden lg:flex" />

          {/* Right Panel — Form */}
          <section className="lg:w-5/12 w-full flex flex-col items-center justify-center p-6 lg:p-8 bg-[#080E1C] relative">
            {/* Subtle gradient overlay */}
            <div className="absolute top-0 right-0 w-full h-full bg-gradient-to-bl from-[#FF1F6D]/5 to-transparent pointer-events-none" />

            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up mb-8">
              {/* Header */}
              <div className="mb-8">
                <h2 className="text-3xl font-display font-extrabold text-white mb-2 tracking-tight">
                  Register Entity
                </h2>
                <p className="text-slate-400 text-sm">
                  Create your neural profile to initialize access.
                </p>
              </div>

              {/* Mobile logo */}
              <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
                <img src="/images/stratum-logo.svg" alt="Stratum AI" className="h-7" style={{ filter: 'invert(1) brightness(2)' }} />
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                {/* API Error */}
                {apiError && (
                  <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400">
                    <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                    <span>{apiError}</span>
                  </div>
                )}

                {/* Name */}
                <div className="space-y-2 auth-fade-up-d1">
                  <label
                    htmlFor="signup-name"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Identity Name
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      {...register('name')}
                      id="signup-name"
                      type="text"
                      placeholder="John Doe"
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-4 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.3)]"
                    />
                  </div>
                  {errors.name && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.name.message}</p>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-2 auth-fade-up-d1">
                  <label
                    htmlFor="signup-email"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Neural Identifier
                  </label>
                  <div className="relative">
                    <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      {...register('email')}
                      id="signup-email"
                      type="email"
                      placeholder="you@company.com"
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-4 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.3)]"
                    />
                  </div>
                  {errors.email && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                  )}
                </div>

                {/* Phone Number */}
                <div className="space-y-2 auth-fade-up-d2">
                  <label
                    htmlFor="signup-phone"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Signal Channel
                  </label>
                  <div className="relative">
                    <PhoneIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      {...register('phone')}
                      id="signup-phone"
                      type="tel"
                      placeholder="+1 234 567 8900"
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-4 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.3)]"
                    />
                  </div>
                  <p className="text-[10px] text-slate-600 ml-1 font-mono">Include country code for WhatsApp verification</p>
                  {errors.phone && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.phone.message}</p>
                  )}
                </div>

                {/* Password */}
                <div className="space-y-2 auth-fade-up-d2">
                  <label
                    htmlFor="signup-password"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Security Key
                  </label>
                  <div className="relative">
                    <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      {...register('password')}
                      id="signup-password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Min. 8 characters"
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-11 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#FF8C00] focus:shadow-[0_0_15px_rgba(255,140,0,0.3)]"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeSlashIcon className="w-[18px] h-[18px]" /> : <EyeIcon className="w-[18px] h-[18px]" />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.password.message}</p>
                  )}
                </div>

                {/* Confirm Password */}
                <div className="space-y-2 auth-fade-up-d2">
                  <label
                    htmlFor="signup-confirm-password"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Confirm Security Key
                  </label>
                  <div className="relative">
                    <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      {...register('confirmPassword')}
                      id="signup-confirm-password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      placeholder="Re-enter security key"
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-11 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#FF8C00] focus:shadow-[0_0_15px_rgba(255,140,0,0.3)]"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    >
                      {showConfirmPassword ? <EyeSlashIcon className="w-[18px] h-[18px]" /> : <EyeIcon className="w-[18px] h-[18px]" />}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="text-xs text-red-400 mt-1 ml-1">{errors.confirmPassword.message}</p>
                  )}
                </div>

                {/* Terms */}
                <div className="flex items-start gap-3 px-1 py-1 auth-fade-up-d3">
                  <input
                    {...register('acceptTerms')}
                    type="checkbox"
                    id="terms"
                    className="mt-0.5 w-4 h-4 rounded border-white/10 bg-[#050B18] text-[#FF1F6D] focus:ring-[#FF1F6D] focus:ring-offset-[#050B18] cursor-pointer"
                  />
                  <label htmlFor="terms" className="text-xs text-slate-400 cursor-pointer select-none">
                    I accept the{' '}
                    <a href="/terms" className="text-[#FF1F6D] font-bold hover:text-white transition-colors">Legal Core</a>
                    {' '}and{' '}
                    <a href="/privacy" className="text-[#FF1F6D] font-bold hover:text-white transition-colors">Privacy Protocol</a>
                  </label>
                </div>
                {errors.acceptTerms && (
                  <p className="text-xs text-red-400 ml-1">{errors.acceptTerms.message}</p>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="auth-fade-up-d3 w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      INITIALIZING...
                    </span>
                  ) : (
                    <>REGISTER ENTITY</>
                  )}
                </button>
              </form>

              {/* Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-4 bg-transparent text-[10px] text-slate-600 uppercase tracking-widest font-mono">
                    Or continue with
                  </span>
                </div>
              </div>

              {/* Social login */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  className="flex items-center justify-center gap-2 h-11 rounded-xl bg-[#050B18]/80 border border-white/10 text-slate-400 text-xs font-bold uppercase tracking-wider hover:border-white/20 hover:text-white transition-all"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Google
                </button>
                <button
                  type="button"
                  className="flex items-center justify-center gap-2 h-11 rounded-xl bg-[#050B18]/80 border border-white/10 text-slate-400 text-xs font-bold uppercase tracking-wider hover:border-white/20 hover:text-white transition-all"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                  </svg>
                  Microsoft
                </button>
              </div>
            </div>

            {/* Footer links */}
            <div className="w-full max-w-md px-10 relative z-10">
              <div className="flex flex-col items-center gap-4">
                <p className="text-center text-[13px] text-white/30">
                  Existing entity?{' '}
                  <Link
                    to="/login"
                    className="text-[#FF1F6D] font-bold hover:text-white transition-colors"
                  >
                    Initialize session
                  </Link>
                </p>
                <div className="flex gap-6">
                  <a className="text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono" href="/privacy">Privacy Protocol</a>
                  <a className="text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono" href="/terms">Legal Core</a>
                  <a className="text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono" href="/contact">Support</a>
                </div>
                <span className="text-[10px] text-slate-600 font-mono tracking-widest">&copy; 2026 STRATUM ARTIFICIAL INTELLIGENCE</span>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
