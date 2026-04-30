/**
 * Signup Page — Stratum figma theme
 * Split-screen: trial pitch + ember-accented signup form (with OTP flow)
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

const FONT_STACK = 'Geist, system-ui, sans-serif';
const MONO_STACK = 'Geist Mono, monospace';

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

const inputClass =
  'w-full h-12 bg-[rgba(255,255,255,0.015)] border border-[#1F1F1F] rounded-[12px] pl-11 pr-4 text-sm text-white placeholder-[#6B6B6B] outline-none focus:ring-4 focus:ring-[#FF5A1F]/[0.12] focus:border-[#FF5A1F]/50 transition-colors';

const labelClass = 'text-[11px] uppercase tracking-[0.12em] text-[#6B6B6B] ml-1';

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11.5px] uppercase tracking-[0.06em] font-medium text-[#ECECEC]"
      style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #1F1F1F' }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full bg-[#FF5A1F]"
        style={{ boxShadow: '0 0 8px #FF5A1F' }}
      />
      {children}
    </span>
  );
}

function PrimaryButton({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="w-full h-12 rounded-full bg-[#FF5A1F] text-white font-medium text-[14px] flex items-center justify-center gap-2 transition-all hover:bg-[#FF6E3A] hover:-translate-y-px disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed"
      style={{ boxShadow: '0 4px 14px rgba(255,90,31,0.3)' }}
    >
      {children}
    </button>
  );
}

function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex bg-[#0B0B0B] text-white" style={{ fontFamily: FONT_STACK }}>
      <AuthLeftPanel />
      <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative overflow-hidden">
        <div
          className="absolute inset-x-0 top-0 h-72 pointer-events-none"
          style={{
            background:
              'radial-gradient(60% 60% at 50% 0%, rgba(255,90,31,0.16) 0%, rgba(255,90,31,0.04) 40%, transparent 70%)',
          }}
          aria-hidden="true"
        />
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

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  const startOTPCountdown = useCallback(() => {
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
        <div className="w-full max-w-[440px] relative z-10">
          <div className="mb-8">
            <div className="w-12 h-12 rounded-[12px] bg-[rgba(255,90,31,0.08)] border border-[#FF5A1F]/30 flex items-center justify-center mb-6">
              <Lock className="w-5 h-5 text-[#FF5A1F]" />
            </div>
            <h2 className="text-[28px] leading-[1.1] tracking-tight font-medium">
              Verify your identity
            </h2>
            <p className="text-[14.5px] text-[#9A9A9A] mt-2">Choose how you'd like to verify.</p>
          </div>

          {(sendEmailOTP.error || sendWhatsAppOTP.error) && (
            <div className="flex items-center gap-2 p-3 rounded-[12px] text-sm bg-red-500/10 border border-red-500/30 text-red-400 mb-6">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{sendEmailOTP.error?.message || sendWhatsAppOTP.error?.message}</span>
            </div>
          )}

          <div className="space-y-3">
            <button
              onClick={handleChooseEmail}
              disabled={isSendingOTP}
              className="w-full flex items-center gap-4 p-4 rounded-[14px] bg-[#141414] border border-[#1F1F1F] hover:border-[#FF5A1F]/40 transition-colors group disabled:opacity-50"
            >
              <div className="w-11 h-11 rounded-[10px] bg-[rgba(255,90,31,0.08)] border border-[#FF5A1F]/30 flex items-center justify-center flex-shrink-0">
                <Mail className="w-5 h-5 text-[#FF5A1F]" />
              </div>
              <div className="text-left flex-1">
                <div className="text-sm font-medium text-white group-hover:text-[#FF5A1F] transition-colors">
                  Verify via Email
                </div>
                <div className="text-xs text-[#6B6B6B] mt-0.5">Send code to {formData?.email}</div>
              </div>
              {sendEmailOTP.isPending && spinner}
            </button>

            <button
              onClick={handleChooseWhatsApp}
              disabled={isSendingOTP || !formData?.phone}
              className="w-full flex items-center gap-4 p-4 rounded-[14px] bg-[#141414] border border-[#1F1F1F] hover:border-emerald-500/40 transition-colors group disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <div className="w-11 h-11 rounded-[10px] bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                <Phone className="w-5 h-5 text-emerald-500" />
              </div>
              <div className="text-left flex-1">
                <div className="text-sm font-medium text-white group-hover:text-emerald-500 transition-colors">
                  Verify via WhatsApp
                </div>
                <div className="text-xs text-[#6B6B6B] mt-0.5">
                  {formData?.phone ? `Send code to ${formData.phone}` : 'No phone number provided'}
                </div>
              </div>
              {sendWhatsAppOTP.isPending && spinner}
            </button>
          </div>

          <div className="flex justify-center mt-8">
            <button
              onClick={() => setStep('details')}
              className="text-xs text-[#9A9A9A] hover:text-white transition-colors font-medium"
            >
              ← Back to registration
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
        <div className="w-full max-w-[440px] relative z-10">
          <div className="mb-8">
            <div className="w-12 h-12 rounded-[12px] bg-[rgba(255,90,31,0.08)] border border-[#FF5A1F]/30 flex items-center justify-center mb-6">
              <Mail className="w-5 h-5 text-[#FF5A1F]" />
            </div>
            <h2 className="text-[28px] leading-[1.1] tracking-tight font-medium">
              Check your email
            </h2>
            <p className="text-[14.5px] text-[#9A9A9A] mt-2 mb-1">We've sent a 6-digit code to</p>
            <p className="text-[#FF5A1F] text-sm font-medium">{formData?.email}</p>
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
              className="w-full text-center text-2xl tracking-[0.5em] h-14 rounded-[12px] bg-[rgba(255,255,255,0.015)] border border-[#1F1F1F] text-white placeholder-[#6B6B6B] focus:ring-4 focus:ring-[#FF5A1F]/[0.12] focus:border-[#FF5A1F]/50 transition-colors outline-none"
              style={{ fontFamily: MONO_STACK }}
              maxLength={6}
            />
            {otpError && <p className="mt-2 text-xs text-red-400 text-center">{otpError}</p>}
          </div>

          <div className="space-y-4">
            <PrimaryButton
              onClick={handleVerifyEmailOTP}
              disabled={isVerifying || otpCode.length !== 6}
            >
              {isVerifying ? (
                <span className="flex items-center gap-2">{spinner} Verifying...</span>
              ) : (
                <>
                  Verify &amp; activate
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </PrimaryButton>

            <div className="flex justify-center">
              <button
                onClick={handleResendOTP}
                disabled={otpCountdown > 0 || sendEmailOTP.isPending}
                className="text-xs text-[#FF5A1F] hover:text-[#FF8A4A] transition-colors disabled:opacity-40 disabled:hover:text-[#FF5A1F] font-medium"
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
                className="text-xs text-[#9A9A9A] hover:text-white transition-colors font-medium"
              >
                ← Try different method
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
        <div className="w-full max-w-[440px] relative z-10">
          <div className="mb-8">
            <div className="w-12 h-12 rounded-[12px] bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-6">
              <Phone className="w-5 h-5 text-emerald-500" />
            </div>
            <h2 className="text-[28px] leading-[1.1] tracking-tight font-medium">
              Check your WhatsApp
            </h2>
            <p className="text-[14.5px] text-[#9A9A9A] mt-2 mb-1">
              We've sent a 6-digit code to your WhatsApp
            </p>
            <p className="text-emerald-500 text-sm font-medium">{formData?.phone}</p>
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
              className="w-full text-center text-2xl tracking-[0.5em] h-14 rounded-[12px] bg-[rgba(255,255,255,0.015)] border border-[#1F1F1F] text-white placeholder-[#6B6B6B] focus:ring-4 focus:ring-[#FF5A1F]/[0.12] focus:border-[#FF5A1F]/50 transition-colors outline-none"
              style={{ fontFamily: MONO_STACK }}
              maxLength={6}
            />
            {otpError && <p className="mt-2 text-xs text-red-400 text-center">{otpError}</p>}
          </div>

          <div className="space-y-4">
            <PrimaryButton
              onClick={handleVerifyWhatsAppOTP}
              disabled={isVerifying || otpCode.length !== 6}
            >
              {isVerifying ? (
                <span className="flex items-center gap-2">{spinner} Verifying...</span>
              ) : (
                <>
                  Verify &amp; activate
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </PrimaryButton>

            <div className="flex justify-center">
              <button
                onClick={handleResendOTP}
                disabled={otpCountdown > 0 || sendWhatsAppOTP.isPending}
                className="text-xs text-[#FF5A1F] hover:text-[#FF8A4A] transition-colors disabled:opacity-40 disabled:hover:text-[#FF5A1F] font-medium"
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
                className="text-xs text-[#9A9A9A] hover:text-white transition-colors font-medium"
              >
                ← Try different method
              </button>
            </div>
          </div>
        </div>
      </AuthLayout>
    );
  }

  // ─── Success Step ───
  // Must be checked BEFORE step-based branches: when signup completes
  // successfully, the `step` state may still be 'verify-email' / 'verify-phone'
  // — without this guard the verify form keeps rendering and the user clicks
  // Verify again, hitting a 400 because the OTP was already consumed.
  if (isSuccess) {
    return (
      <AuthLayout>
        <div className="w-full max-w-[440px] relative z-10 text-center">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="text-[28px] leading-[1.1] tracking-tight font-medium">Account created</h2>
          <p className="text-[14.5px] text-[#9A9A9A] mt-3 mb-6">
            Your profile is ready and your{' '}
            <span className="text-[#FF5A1F] font-medium">Free Tier</span> is now active.
          </p>

          <div className="rounded-[14px] border border-[#1F1F1F] bg-[#141414] p-5 mb-6 text-left">
            <p
              className="text-[11px] text-[#FF5A1F] font-medium uppercase tracking-[0.12em] mb-2"
              style={{ fontFamily: MONO_STACK }}
            >
              Free Plan Active
            </p>
            <p className="text-[13px] text-[#9A9A9A] leading-relaxed">
              Upgrade to <span className="text-white font-medium">Starter</span>,{' '}
              <span className="text-white font-medium">Professional</span>, or{' '}
              <span className="text-white font-medium">Enterprise</span> to unlock advanced
              automation, unlimited campaigns, and priority support.
            </p>
            <button
              onClick={() => navigate('/login', { state: { registered: true, showUpgrade: true } })}
              className="mt-4 text-xs text-[#FF5A1F] hover:text-[#FF8A4A] transition-colors font-medium"
            >
              View plans →
            </button>
          </div>

          <PrimaryButton onClick={() => navigate('/login', { state: { registered: true } })}>
            Sign in
            <ArrowRight className="w-4 h-4" />
          </PrimaryButton>
        </div>
      </AuthLayout>
    );
  }

  // ─── Main Signup Form ───
  return (
    <>
      <SEO {...pageSEO.signup} url="https://stratum-ai.com/signup" />

      <div className="min-h-screen flex bg-[#0B0B0B] text-white" style={{ fontFamily: FONT_STACK }}>
        <AuthLeftPanel />

        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative overflow-hidden">
          <div
            className="absolute inset-x-0 top-0 h-72 pointer-events-none"
            style={{
              background:
                'radial-gradient(60% 60% at 50% 0%, rgba(255,90,31,0.16) 0%, rgba(255,90,31,0.04) 40%, transparent 70%)',
            }}
            aria-hidden="true"
          />

          {/* Mobile wordmark */}
          <div className="lg:hidden mb-8 self-start">
            <a href="/landing.html" className="text-[18px] font-medium tracking-tight text-white">
              stratum.ai
            </a>
          </div>

          <div className="w-full max-w-[440px] relative z-10">
            {/* Heading */}
            <div className="mb-8">
              <Pill>Create account</Pill>
              <h1 className="text-[32px] leading-[1.1] tracking-tight font-medium mt-5">
                Start in under a minute.
              </h1>
              <p className="text-[14.5px] text-[#9A9A9A] mt-2">Provision your secure workspace.</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {apiError && (
                <div className="flex items-center gap-2 p-3 rounded-[12px] text-sm bg-red-500/10 border border-red-500/30 text-red-400">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{apiError}</span>
                </div>
              )}

              {/* Name */}
              <div className="space-y-2">
                <label
                  htmlFor="signup-name"
                  className={labelClass}
                  style={{ fontFamily: MONO_STACK }}
                >
                  Full name
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
                  <input
                    {...register('name')}
                    id="signup-name"
                    type="text"
                    placeholder="Jane Doe"
                    className={inputClass}
                  />
                </div>
                {errors.name && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.name.message}</p>
                )}
              </div>

              {/* Email */}
              <div className="space-y-2">
                <label
                  htmlFor="signup-email"
                  className={labelClass}
                  style={{ fontFamily: MONO_STACK }}
                >
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
                  <input
                    {...register('email')}
                    id="signup-email"
                    type="email"
                    placeholder="you@company.com"
                    className={inputClass}
                  />
                </div>
                {errors.email && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                )}
              </div>

              {/* Phone */}
              <div className="space-y-2">
                <label
                  htmlFor="signup-phone"
                  className={labelClass}
                  style={{ fontFamily: MONO_STACK }}
                >
                  Phone <span className="normal-case text-[#6B6B6B]">(optional)</span>
                </label>
                <div className="relative">
                  <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
                  <input
                    {...register('phone')}
                    id="signup-phone"
                    type="tel"
                    placeholder="+1 234 567 8900"
                    className={inputClass}
                  />
                </div>
                <p className="text-xs text-[#6B6B6B] ml-1">
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
                  className={labelClass}
                  style={{ fontFamily: MONO_STACK }}
                >
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
                  <input
                    {...register('password')}
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    className={inputClass.replace('pr-4', 'pr-11')}
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B6B6B] hover:text-white transition-colors"
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
                  className={labelClass}
                  style={{ fontFamily: MONO_STACK }}
                >
                  Confirm password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
                  <input
                    {...register('confirmPassword')}
                    id="signup-confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Re-enter password"
                    className={inputClass.replace('pr-4', 'pr-11')}
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B6B6B] hover:text-white transition-colors"
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
              <label className="flex items-start gap-2.5 select-none cursor-pointer pt-1">
                <input
                  {...register('acceptTerms')}
                  type="checkbox"
                  id="terms"
                  className="mt-0.5 w-4 h-4 rounded border border-[#262626] bg-[#141414] accent-[#FF5A1F] cursor-pointer flex-shrink-0"
                />
                <span className="text-[13px] text-[#9A9A9A] leading-relaxed">
                  I accept the{' '}
                  <a
                    href="/terms"
                    className="text-white hover:text-[#FF5A1F] transition-colors font-medium"
                  >
                    Terms
                  </a>{' '}
                  and{' '}
                  <a
                    href="/privacy"
                    className="text-white hover:text-[#FF5A1F] transition-colors font-medium"
                  >
                    Privacy Policy
                  </a>
                </span>
              </label>
              {errors.acceptTerms && (
                <p className="text-xs text-red-400 ml-1">{errors.acceptTerms.message}</p>
              )}

              {/* Submit */}
              <PrimaryButton type="submit" disabled={isLoading}>
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    {spinner}
                    Creating account...
                  </span>
                ) : (
                  <>
                    Create account
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </PrimaryButton>
            </form>

            {/* Footer */}
            <div className="mt-10 pt-6 border-t border-[#1F1F1F]">
              <p className="text-[13px] text-[#9A9A9A]">
                Already have an account?
                <Link
                  to="/login"
                  className="text-white hover:text-[#FF5A1F] transition-colors font-medium ml-1"
                >
                  Sign in
                </Link>
              </p>
              <div
                className="mt-6 flex items-center gap-5 text-[11px] uppercase tracking-[0.12em] text-[#6B6B6B]"
                style={{ fontFamily: MONO_STACK }}
              >
                <a href="/privacy" className="hover:text-white transition-colors">
                  Privacy
                </a>
                <a href="/terms" className="hover:text-white transition-colors">
                  Terms
                </a>
                <a href="/contact" className="hover:text-white transition-colors">
                  Support
                </a>
              </div>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
