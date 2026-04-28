/**
 * Signup Page - Stratum AI
 * Command Center design system — split-screen layout
 * Verification required via Email or WhatsApp before registration completes
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Eye,
  EyeOff,
  Mail,
  Lock,
  User,
  Phone,
  CheckCircle,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import {
  useSignup,
  useSendWhatsAppOTP,
  useVerifyWhatsAppOTP,
  useSendEmailOTP,
  useVerifyEmailOTP,
} from '@/api/auth';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

const signupSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email'),
    phone: z.string(),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
    acceptTerms: z.boolean().refine((val) => val === true, 'You must accept the terms'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type SignupForm = z.infer<typeof signupSchema>;

type SignupStep = 'details' | 'choose-method' | 'verify-email' | 'verify-phone' | 'success';

function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
      <AuthLeftPanel />
      <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
        {children}
      </section>
    </div>
  );
}

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
    signupMutation.error?.message || sendWhatsAppOTP.error?.message || sendEmailOTP.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { phone: '' },
  });

  // Timer ref for cleanup on unmount / restart
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup interval on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  // When the signup mutation succeeds, transition the step to 'success' so the
  // user sees the "Account created" screen instead of remaining on the verify
  // form. Without this, step stays at 'verify-email' / 'verify-phone' and the
  // step-based render branches return their UI before the isSuccess block
  // is ever reached — the user clicks Verify again and hits 400 because the
  // OTP was already consumed.
  useEffect(() => {
    if (isSuccess && step !== 'success') {
      setStep('success');
    }
  }, [isSuccess, step]);

  // Start countdown timer for OTP resend
  const startOTPCountdown = useCallback(() => {
    // Clear any existing timer before starting a new one
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setOtpCountdown(60);
    timerRef.current = setInterval(() => {
      setOtpCountdown((prev) => {
        if (prev <= 1) {
          if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

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
        {
          onSuccess: () => {
            startOTPCountdown();
            setOtpCode('');
            setOtpError('');
          },
        }
      );
    } else if (step === 'verify-phone') {
      sendWhatsAppOTP.mutate(
        { phone_number: formData.phone || '' },
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

  const isSendingOTP = sendEmailOTP.isPending || sendWhatsAppOTP.isPending;
  const isVerifying =
    verifyEmailOTP.isPending || verifyWhatsAppOTP.isPending || signupMutation.isPending;

  // Loading spinner
  const spinner = (
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
  );

  // ─── Choose Verification Method ───
  if (step === 'choose-method') {
    return (
      <AuthLayout>
        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
          <div className="text-left mb-8">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00]/10 border border-[#FF8C00]/20 flex items-center justify-center mb-6">
              <Lock className="w-6 h-6 text-[#FF8C00]" />
            </div>
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">Verify your identity</h2>
            <p className="text-sm text-[#8B92A8]">Choose how you'd like to verify your identity</p>
          </div>

          {(sendEmailOTP.error || sendWhatsAppOTP.error) && (
            <div className="flex items-center gap-2 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400 mb-6">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{sendEmailOTP.error?.message || sendWhatsAppOTP.error?.message}</span>
            </div>
          )}

          <div className="space-y-4">
            {/* Email Verification */}
            <button
              onClick={handleChooseEmail}
              disabled={isSendingOTP}
              className="w-full flex items-center gap-4 p-4 rounded-lg bg-[#181F33] border border-[#1E2740] hover:border-[#FF8C00]/40 transition-colors duration-200 group disabled:opacity-50"
            >
              <div className="w-12 h-12 rounded-lg bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00]/10 border border-[#FF8C00]/20 flex items-center justify-center flex-shrink-0">
                <Mail className="w-6 h-6 text-[#FF8C00]" />
              </div>
              <div className="text-left flex-1">
                <div className="text-sm font-semibold text-[#F0EDE5] group-hover:text-[#FF8C00] transition-colors duration-200">
                  Verify via Email
                </div>
                <div className="text-xs text-[#5A6278] mt-0.5">Send code to {formData?.email}</div>
              </div>
              {sendEmailOTP.isPending && spinner}
            </button>

            {/* WhatsApp Verification */}
            <button
              onClick={handleChooseWhatsApp}
              disabled={isSendingOTP || !formData?.phone}
              className="w-full flex items-center gap-4 p-4 rounded-lg bg-[#181F33] border border-[#1E2740] hover:border-emerald-500/40 transition-colors duration-200 group disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <div className="w-12 h-12 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                <Phone className="w-6 h-6 text-emerald-500" />
              </div>
              <div className="text-left flex-1">
                <div className="text-sm font-semibold text-[#F0EDE5] group-hover:text-emerald-500 transition-colors duration-200">
                  Verify via WhatsApp
                </div>
                <div className="text-xs text-[#5A6278] mt-0.5">
                  {formData?.phone ? `Send code to ${formData.phone}` : 'No phone number provided'}
                </div>
              </div>
              {sendWhatsAppOTP.isPending && spinner}
            </button>
          </div>

          <div className="flex justify-center mt-6">
            <button
              onClick={() => setStep('details')}
              className="text-xs text-[#8B92A8] hover:text-[#FFB347] transition-colors duration-200 font-medium"
            >
              &larr; Back to registration
            </button>
          </div>
        </div>
      </AuthLayout>
    );
  }

  // ─── OTP Verification (Email) ───
  if (step === 'verify-email') {
    return (
      <AuthLayout>
        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
          <div className="text-left mb-8">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00]/10 border border-[#FF8C00]/20 flex items-center justify-center mb-6">
              <Mail className="w-6 h-6 text-[#FF8C00]" />
            </div>
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">Check your email</h2>
            <p className="text-sm text-[#8B92A8] mb-1">We've sent a 6-digit code to</p>
            <p className="text-[#FF8C00] text-sm font-semibold">{formData?.email}</p>
          </div>

          <div className="mb-6">
            <input
              type="text"
              value={otpCode}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                setOtpCode(value);
                setOtpError('');
              }}
              placeholder="000000"
              aria-label="One-time password"
              className="w-full text-center text-2xl tracking-[0.5em] h-14 rounded-lg bg-[#181F33] border border-[#1E2740] text-[#F0EDE5] placeholder-[#5A6278] focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200 outline-none font-mono"
              maxLength={6}
            />
            {otpError && <p className="mt-2 text-xs text-red-400 text-center">{otpError}</p>}
          </div>

          <div className="space-y-4">
            <button
              onClick={handleVerifyEmailOTP}
              disabled={isVerifying || otpCode.length !== 6}
              className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isVerifying ? (
                <span className="flex items-center gap-2">{spinner} Verifying...</span>
              ) : (
                'Verify & activate'
              )}
            </button>

            <div className="flex justify-center">
              <button
                onClick={handleResendOTP}
                disabled={otpCountdown > 0 || sendEmailOTP.isPending}
                className="text-xs text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 disabled:opacity-40 disabled:hover:text-[#FF8C00] font-medium"
              >
                {sendEmailOTP.isPending
                  ? 'Sending...'
                  : otpCountdown > 0
                    ? `Resend in ${otpCountdown}s`
                    : 'Resend code'}
              </button>
            </div>

            <div className="flex justify-center">
              <button
                onClick={() => setStep('choose-method')}
                className="text-xs text-[#8B92A8] hover:text-[#FFB347] transition-colors duration-200 font-medium"
              >
                &larr; Try different method
              </button>
            </div>
          </div>
        </div>
      </AuthLayout>
    );
  }

  // ─── OTP Verification (WhatsApp) ───
  if (step === 'verify-phone') {
    return (
      <AuthLayout>
        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
          <div className="text-left mb-8">
            <div className="w-12 h-12 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-6">
              <Phone className="w-6 h-6 text-emerald-500" />
            </div>
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">Check your WhatsApp</h2>
            <p className="text-sm text-[#8B92A8] mb-1">
              We've sent a 6-digit code to your WhatsApp
            </p>
            <p className="text-emerald-500 text-sm font-semibold">{formData?.phone}</p>
          </div>

          <div className="mb-6">
            <input
              type="text"
              value={otpCode}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                setOtpCode(value);
                setOtpError('');
              }}
              placeholder="000000"
              aria-label="One-time password"
              className="w-full text-center text-2xl tracking-[0.5em] h-14 rounded-lg bg-[#181F33] border border-[#1E2740] text-[#F0EDE5] placeholder-[#5A6278] focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200 outline-none font-mono"
              maxLength={6}
            />
            {otpError && <p className="mt-2 text-xs text-red-400 text-center">{otpError}</p>}
          </div>

          <div className="space-y-4">
            <button
              onClick={handleVerifyWhatsAppOTP}
              disabled={isVerifying || otpCode.length !== 6}
              className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isVerifying ? (
                <span className="flex items-center gap-2">{spinner} Verifying...</span>
              ) : (
                'Verify & activate'
              )}
            </button>

            <div className="flex justify-center">
              <button
                onClick={handleResendOTP}
                disabled={otpCountdown > 0 || sendWhatsAppOTP.isPending}
                className="text-xs text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 disabled:opacity-40 disabled:hover:text-[#FF8C00] font-medium"
              >
                {sendWhatsAppOTP.isPending
                  ? 'Sending...'
                  : otpCountdown > 0
                    ? `Resend in ${otpCountdown}s`
                    : 'Resend code'}
              </button>
            </div>

            <div className="flex justify-center">
              <button
                onClick={() => setStep('choose-method')}
                className="text-xs text-[#8B92A8] hover:text-[#FFB347] transition-colors duration-200 font-medium"
              >
                &larr; Try different method
              </button>
            </div>
          </div>
        </div>
      </AuthLayout>
    );
  }

  // ─── Success Step ───
  // Must be checked BEFORE step-based branches: when signup completes
  // successfully, the `step` state is still 'verify-email' (or 'verify-phone'),
  // so without this guard the verify form keeps rendering and the user
  // clicks Verify again, hitting a 400 because the OTP was already consumed.
  if (isSuccess) {
    return (
      <AuthLayout>
        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">Account created</h2>
          <p className="text-sm text-[#8B92A8] mb-4">
            Your profile has been created and your{' '}
            <span className="text-[#FF8C00] font-semibold">Free Tier</span> is now active.
          </p>

          {/* Free Tier Banner */}
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 mb-6 text-left">
            <p className="text-xs text-amber-500 font-semibold uppercase tracking-wider mb-1">
              Free Plan Active
            </p>
            <p className="text-xs text-[#8B92A8]">
              Upgrade to <span className="text-[#F0EDE5] font-medium">Starter</span>,{' '}
              <span className="text-[#F0EDE5] font-medium">Professional</span>, or{' '}
              <span className="text-[#F0EDE5] font-medium">Enterprise</span> to unlock advanced
              automation, unlimited campaigns, and priority support.
            </p>
            <button
              onClick={() => navigate('/login', { state: { registered: true, showUpgrade: true } })}
              className="mt-3 text-xs text-amber-500 hover:text-[#FFB347] transition-colors duration-200 font-medium"
            >
              View Plans &rarr;
            </button>
          </div>

          <button
            onClick={() => navigate('/login', { state: { registered: true } })}
            className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 inline-flex items-center justify-center gap-2"
          >
            Sign in
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </AuthLayout>
    );
  }

  // ─── Main Signup Form ───
  return (
    <>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />

      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />

        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          {/* Mobile logo */}
          <div className="lg:hidden mb-8">
            <img
              src="/images/stratum-logo.png"
              alt="Stratum AI"
              className="h-8"
              loading="lazy"
              decoding="async"
            />
          </div>

          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
                Let's build something great together.
              </h1>
              <p className="text-sm text-[#8B92A8]">Create your account to get started.</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* API Error */}
              {apiError && (
                <div className="flex items-center gap-2 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{apiError}</span>
                </div>
              )}

              {/* Name */}
              <div className="space-y-2">
                <label htmlFor="signup-name" className="text-xs font-medium text-[#8B92A8] ml-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    {...register('name')}
                    id="signup-name"
                    type="text"
                    placeholder="John Doe"
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-4 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                  />
                </div>
                {errors.name && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.name.message}</p>
                )}
              </div>

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="signup-email" className="text-xs font-medium text-[#8B92A8] ml-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    {...register('email')}
                    id="signup-email"
                    type="email"
                    placeholder="you@company.com"
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-4 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                  />
                </div>
                {errors.email && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                )}
              </div>

              {/* Phone Number (optional) */}
              <div className="space-y-2">
                <label htmlFor="signup-phone" className="text-xs font-medium text-[#8B92A8] ml-1">
                  Phone <span className="text-[#5A6278] normal-case">(optional)</span>
                </label>
                <div className="relative">
                  <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    {...register('phone')}
                    id="signup-phone"
                    type="tel"
                    placeholder="+1 234 567 8900"
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-4 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                  />
                </div>
                <p className="text-xs text-[#5A6278] ml-1">
                  Include country code to enable WhatsApp verification
                </p>
                {errors.phone && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.phone.message}</p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label
                  htmlFor="signup-password"
                  className="text-xs font-medium text-[#8B92A8] ml-1"
                >
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    {...register('password')}
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-11 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                  />
                  <button
                    type="button"
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#5A6278] hover:text-[#8B92A8] transition-colors duration-200"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <label
                  htmlFor="signup-confirm-password"
                  className="text-xs font-medium text-[#8B92A8] ml-1"
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    {...register('confirmPassword')}
                    id="signup-confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Re-enter password"
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-11 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                  />
                  <button
                    type="button"
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#5A6278] hover:text-[#8B92A8] transition-colors duration-200"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.confirmPassword.message}</p>
                )}
              </div>

              {/* Terms */}
              <div className="flex items-start gap-3 px-1 py-1">
                <input
                  {...register('acceptTerms')}
                  type="checkbox"
                  id="terms"
                  className="mt-0.5 w-4 h-4 rounded border-[#1E2740] bg-[#181F33] text-[#FF8C00] focus:ring-[#FF8C00]/30 focus:ring-offset-0 cursor-pointer"
                />
                <label
                  htmlFor="terms"
                  className="text-xs text-[#8B92A8] cursor-pointer select-none"
                >
                  I accept the{' '}
                  <a
                    href="/terms"
                    className="text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 font-medium"
                  >
                    Terms
                  </a>{' '}
                  and{' '}
                  <a
                    href="/privacy"
                    className="text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 font-medium"
                  >
                    Privacy Policy
                  </a>
                </label>
              </div>
              {errors.acceptTerms && (
                <p className="text-xs text-red-400 ml-1">{errors.acceptTerms.message}</p>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    {spinner}
                    Creating account...
                  </span>
                ) : (
                  'Create account'
                )}
              </button>
            </form>
          </div>

          {/* Footer links */}
          <div className="w-full max-w-md mt-8 text-center">
            <p className="text-sm text-[#5A6278]">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 font-medium"
              >
                Sign in
              </Link>
            </p>
            <div className="mt-6 flex items-center justify-center gap-6 text-xs text-[#5A6278]">
              <a href="/privacy" className="hover:text-[#8B92A8] transition-colors duration-200">
                Privacy
              </a>
              <a href="/terms" className="hover:text-[#8B92A8] transition-colors duration-200">
                Terms
              </a>
              <a href="/contact" className="hover:text-[#8B92A8] transition-colors duration-200">
                Support
              </a>
            </div>
            <p className="mt-6 text-[10px] text-[#5A6278] tracking-wider">&copy; 2026 STRATUM AI</p>
          </div>
        </section>
      </div>
    </>
  );
}
