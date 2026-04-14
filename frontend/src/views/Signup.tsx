/**
 * Signup Page - Stratum AI
 * Split-screen layout: Trust Gauge left panel + glass card form
 * Cyberpunk Dark theme — midnight navy + spectral pink/orange/gold
 * Verification required via Email or WhatsApp before registration completes
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
import {
  useSignup,
  useSendWhatsAppOTP,
  useVerifyWhatsAppOTP,
  useSendEmailOTP,
  useVerifyEmailOTP,
} from '@/api/auth';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

const signupSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email'),
  phone: z.string(),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  acceptTerms: z.boolean().refine(val => val === true, 'You must accept the terms'),
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type SignupForm = z.infer<typeof signupSchema>;

type SignupStep = 'details' | 'choose-method' | 'verify-email' | 'verify-phone' | 'success';

export default function Signup() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [step, setStep] = useState<SignupStep>('details');
  const [formData, setFormData] = useState<SignupForm | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [otpError, setOtpError] = useState('');
  const [otpCountdown, setOtpCountdown] = useState(0);

  const signupMutation = useSignup();
  const sendWhatsAppOTP = useSendWhatsAppOTP();
  const verifyWhatsAppOTP = useVerifyWhatsAppOTP();
  const sendEmailOTP = useSendEmailOTP();
  const verifyEmailOTP = useVerifyEmailOTP();

  const isLoading = signupMutation.isPending || sendWhatsAppOTP.isPending || sendEmailOTP.isPending;
  const isSuccess = signupMutation.isSuccess;
  const apiError =
    signupMutation.error?.message ||
    sendWhatsAppOTP.error?.message ||
    sendEmailOTP.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { phone: '' },
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

  const onSubmit = (data: SignupForm) => {
    setFormData(data);
    setStep('choose-method');
  };

  // Send verification OTP based on chosen method
  const handleChooseEmail = () => {
    if (!formData) return;
    sendEmailOTP.mutate(
      { email: formData.email },
      {
        onSuccess: () => {
          setStep('verify-email');
          setOtpCode('');
          setOtpError('');
          startOTPCountdown();
        },
      }
    );
  };

  const handleChooseWhatsApp = () => {
    if (!formData || !formData.phone) return;
    sendWhatsAppOTP.mutate(
      { phone_number: formData.phone },
      {
        onSuccess: () => {
          setStep('verify-phone');
          setOtpCode('');
          setOtpError('');
          startOTPCountdown();
        },
      }
    );
  };

  // Complete registration after OTP verification
  const completeRegistration = (verificationToken: string) => {
    if (!formData) return;
    signupMutation.mutate({
      full_name: formData.name,
      email: formData.email,
      password: formData.password,
      phone: formData.phone || undefined,
      company_website: '',
      verification_token: verificationToken,
    });
  };

  // Verify email OTP
  const handleVerifyEmailOTP = () => {
    if (!formData || otpCode.length !== 6) {
      setOtpError('Please enter a valid 6-digit code');
      return;
    }
    setOtpError('');
    verifyEmailOTP.mutate(
      { email: formData.email, otp_code: otpCode },
      {
        onSuccess: (response) => {
          completeRegistration(response.verification_token || '');
        },
        onError: (error) => {
          setOtpError(error.message || 'Invalid OTP code');
        },
      }
    );
  };

  // Verify WhatsApp OTP
  const handleVerifyWhatsAppOTP = () => {
    if (!formData || otpCode.length !== 6) {
      setOtpError('Please enter a valid 6-digit code');
      return;
    }
    setOtpError('');
    verifyWhatsAppOTP.mutate(
      { phone_number: formData.phone || '', otp_code: otpCode },
      {
        onSuccess: (response) => {
          completeRegistration(response.verification_token || '');
        },
        onError: (error) => {
          setOtpError(error.message || 'Invalid OTP code');
        },
      }
    );
  };

  // Resend OTP for current method
  const handleResendOTP = () => {
    if (!formData || otpCountdown > 0) return;
    if (step === 'verify-email') {
      sendEmailOTP.mutate(
        { email: formData.email },
        { onSuccess: () => { startOTPCountdown(); setOtpCode(''); setOtpError(''); } }
      );
    } else if (step === 'verify-phone') {
      sendWhatsAppOTP.mutate(
        { phone_number: formData.phone || '' },
        { onSuccess: () => { startOTPCountdown(); setOtpCode(''); setOtpError(''); } }
      );
    }
  };

  const isSendingOTP = sendEmailOTP.isPending || sendWhatsAppOTP.isPending;
  const isVerifying = verifyEmailOTP.isPending || verifyWhatsAppOTP.isPending || signupMutation.isPending;

  // Shared background elements
  const bgElements = (
    <>
      <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
        <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
      </div>
    </>
  );

  // Shared OTP input
  const otpInput = (
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
  );

  // Loading spinner
  const spinner = (
    <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );

  // ─── Choose Verification Method ───
  if (step === 'choose-method') {
    return (
      <>
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          {bgElements}
          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up">
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-full bg-[#00F5FF]/10 border border-[#00F5FF]/20 flex items-center justify-center mx-auto mb-6">
                  <LockClosedIcon className="w-8 h-8 text-[#00F5FF]" />
                </div>
                <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                  Verify Identity
                </h2>
                <p className="text-slate-400 text-sm">
                  Choose how you'd like to verify your identity
                </p>
              </div>

              {(sendEmailOTP.error || sendWhatsAppOTP.error) && (
                <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400 mb-6">
                  <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                  <span>{sendEmailOTP.error?.message || sendWhatsAppOTP.error?.message}</span>
                </div>
              )}

              <div className="space-y-4 auth-fade-up-d1">
                {/* Email Verification */}
                <button
                  onClick={handleChooseEmail}
                  disabled={isSendingOTP}
                  className="w-full flex items-center gap-4 p-4 rounded-xl bg-[#050B18]/80 border border-white/10 hover:border-[#00F5FF]/50 hover:shadow-[0_0_20px_rgba(0,245,255,0.1)] transition-all group disabled:opacity-50"
                >
                  <div className="w-12 h-12 rounded-lg bg-[#00F5FF]/10 border border-[#00F5FF]/20 flex items-center justify-center flex-shrink-0">
                    <EnvelopeIcon className="w-6 h-6 text-[#00F5FF]" />
                  </div>
                  <div className="text-left flex-1">
                    <div className="text-sm font-bold text-white group-hover:text-[#00F5FF] transition-colors">
                      Verify via Email
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      Send code to {formData?.email}
                    </div>
                  </div>
                  {sendEmailOTP.isPending && spinner}
                </button>

                {/* WhatsApp Verification */}
                <button
                  onClick={handleChooseWhatsApp}
                  disabled={isSendingOTP || !formData?.phone}
                  className="w-full flex items-center gap-4 p-4 rounded-xl bg-[#050B18]/80 border border-white/10 hover:border-[#25D366]/50 hover:shadow-[0_0_20px_rgba(37,211,102,0.1)] transition-all group disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <div className="w-12 h-12 rounded-lg bg-[#25D366]/10 border border-[#25D366]/20 flex items-center justify-center flex-shrink-0">
                    <PhoneIcon className="w-6 h-6 text-[#25D366]" />
                  </div>
                  <div className="text-left flex-1">
                    <div className="text-sm font-bold text-white group-hover:text-[#25D366] transition-colors">
                      Verify via WhatsApp
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {formData?.phone ? `Send code to ${formData.phone}` : 'No phone number provided'}
                    </div>
                  </div>
                  {sendWhatsAppOTP.isPending && spinner}
                </button>
              </div>

              <div className="flex justify-center mt-6">
                <button
                  onClick={() => setStep('details')}
                  className="text-xs text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono"
                >
                  &larr; Back to registration
                </button>
              </div>
            </div>
          </main>
        </div>
      </>
    );
  }

  // ─── OTP Verification (Email) ───
  if (step === 'verify-email') {
    return (
      <>
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          {bgElements}
          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up">
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-full bg-[#00F5FF]/10 border border-[#00F5FF]/20 flex items-center justify-center mx-auto mb-6">
                  <EnvelopeIcon className="w-8 h-8 text-[#00F5FF]" />
                </div>
                <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                  Check Your Email
                </h2>
                <p className="text-slate-400 text-sm mb-1">
                  We've sent a 6-digit code to
                </p>
                <p className="text-[#00F5FF] font-mono text-sm font-bold">
                  {formData?.email}
                </p>
              </div>

              {otpInput}

              <div className="space-y-4 auth-fade-up-d2">
                <button
                  onClick={handleVerifyEmailOTP}
                  disabled={isVerifying || otpCode.length !== 6}
                  className="w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {isVerifying ? (
                    <span className="flex items-center gap-2">{spinner} VERIFYING...</span>
                  ) : (
                    'VERIFY & ACTIVATE'
                  )}
                </button>

                <div className="flex justify-center">
                  <button
                    onClick={handleResendOTP}
                    disabled={otpCountdown > 0 || sendEmailOTP.isPending}
                    className="text-xs text-[#FF1F6D] hover:text-white transition-colors disabled:opacity-40 disabled:hover:text-[#FF1F6D] font-bold uppercase tracking-widest"
                  >
                    {sendEmailOTP.isPending ? 'Sending...' : otpCountdown > 0 ? `Resend in ${otpCountdown}s` : 'Resend Code'}
                  </button>
                </div>

                <div className="flex justify-center">
                  <button
                    onClick={() => setStep('choose-method')}
                    className="text-xs text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono"
                  >
                    &larr; Try different method
                  </button>
                </div>
              </div>
            </div>
          </main>
        </div>
      </>
    );
  }

  // ─── OTP Verification (WhatsApp) ───
  if (step === 'verify-phone') {
    return (
      <>
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          {bgElements}
          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up">
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-full bg-[#25D366]/10 border border-[#25D366]/20 flex items-center justify-center mx-auto mb-6">
                  <PhoneIcon className="w-8 h-8 text-[#25D366]" />
                </div>
                <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                  Verify Signal Channel
                </h2>
                <p className="text-slate-400 text-sm mb-1">
                  We've transmitted a 6-digit code to your WhatsApp
                </p>
                <p className="text-[#25D366] font-mono text-sm font-bold">
                  {formData?.phone}
                </p>
              </div>

              {otpInput}

              <div className="space-y-4 auth-fade-up-d2">
                <button
                  onClick={handleVerifyWhatsAppOTP}
                  disabled={isVerifying || otpCode.length !== 6}
                  className="w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {isVerifying ? (
                    <span className="flex items-center gap-2">{spinner} VERIFYING...</span>
                  ) : (
                    'VERIFY & ACTIVATE'
                  )}
                </button>

                <div className="flex justify-center">
                  <button
                    onClick={handleResendOTP}
                    disabled={otpCountdown > 0 || sendWhatsAppOTP.isPending}
                    className="text-xs text-[#FF1F6D] hover:text-white transition-colors disabled:opacity-40 disabled:hover:text-[#FF1F6D] font-bold uppercase tracking-widest"
                  >
                    {sendWhatsAppOTP.isPending ? 'Transmitting...' : otpCountdown > 0 ? `Retransmit in ${otpCountdown}s` : 'Retransmit Code'}
                  </button>
                </div>

                <div className="flex justify-center">
                  <button
                    onClick={() => setStep('choose-method')}
                    className="text-xs text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono"
                  >
                    &larr; Try different method
                  </button>
                </div>
              </div>
            </div>
          </main>
        </div>
      </>
    );
  }

  // ─── Success Step ───
  if (isSuccess) {
    return (
      <>
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          {bgElements}
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
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
              <p className="text-slate-400 text-sm mb-4">
                Your neural profile has been created and your <span className="text-[#00F5FF] font-bold">Free Tier</span> is now active.
              </p>

              {/* Free Tier Banner */}
              <div className="rounded-lg border border-[#FF8C00]/20 bg-[#FF8C00]/5 p-4 mb-6">
                <p className="text-xs text-[#FF8C00] font-bold uppercase tracking-wider mb-1">
                  Free Plan Active
                </p>
                <p className="text-xs text-slate-400">
                  Upgrade to <span className="text-white font-semibold">Starter</span>, <span className="text-white font-semibold">Professional</span>, or <span className="text-white font-semibold">Enterprise</span> to unlock advanced automation, unlimited campaigns, and priority support.
                </p>
                <button
                  onClick={() => navigate('/login', { state: { registered: true, showUpgrade: true } })}
                  className="mt-3 text-[10px] text-[#FF8C00] hover:text-white transition-colors font-bold uppercase tracking-widest"
                >
                  View Plans &rarr;
                </button>
              </div>

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

  // ─── Main Signup Form ───
  return (
    <>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />
      <style>{authStyles}</style>

      <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
        {bgElements}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
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

                {/* Phone Number (optional) */}
                <div className="space-y-2 auth-fade-up-d2">
                  <label
                    htmlFor="signup-phone"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Signal Channel <span className="text-slate-600 normal-case">(optional)</span>
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
                  <p className="text-[10px] text-slate-600 ml-1 font-mono">Include country code to enable WhatsApp verification</p>
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
                      {spinner}
                      INITIALIZING...
                    </span>
                  ) : (
                    <>CONTINUE</>
                  )}
                </button>
              </form>
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
