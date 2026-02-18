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
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full">
          <div className="motion-enter text-center">
            <div className="w-20 h-20 rounded-full bg-stratum-500/10 flex items-center justify-center mx-auto mb-6">
              <PhoneIcon className="w-10 h-10 text-stratum-400" />
            </div>
            <h1 className="text-h1 text-white mb-4">Verify your WhatsApp</h1>
            <p className="text-body text-text-secondary mb-2">
              We've sent a 6-digit code to your WhatsApp
            </p>
            <p className="text-body text-stratum-400 font-medium mb-8">
              {formData?.phone}
            </p>

            {/* OTP Input */}
            <div className="mb-6">
              <input
                type="text"
                value={otpCode}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                  setOtpCode(value);
                  setOtpError('');
                }}
                placeholder="Enter 6-digit code"
                className="w-full text-center text-2xl tracking-[0.5em] py-4 rounded-xl bg-surface-secondary border border-white/10
                           text-white placeholder-text-muted
                           focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                           transition-all duration-base outline-none"
                maxLength={6}
              />
              {otpError && (
                <p className="mt-2 text-meta text-danger">{otpError}</p>
              )}
            </div>

            <div className="space-y-4">
              <button
                onClick={handleVerifyOTP}
                disabled={verifyOTPMutation.isPending || otpCode.length !== 6}
                className="w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body
                           hover:shadow-glow transition-all duration-base
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {verifyOTPMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Verifying...
                  </span>
                ) : (
                  'Verify & Create Account'
                )}
              </button>

              <button
                onClick={handleResendOTP}
                disabled={otpCountdown > 0 || sendOTPMutation.isPending}
                className="text-meta text-stratum-400 hover:text-stratum-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sendOTPMutation.isPending ? (
                  'Sending...'
                ) : otpCountdown > 0 ? (
                  `Resend code in ${otpCountdown}s`
                ) : (
                  'Resend code'
                )}
              </button>

              <button
                onClick={() => setStep('details')}
                className="block w-full text-meta text-text-muted hover:text-text-secondary transition-colors"
              >
                ← Back to signup
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            <div className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-6">
              <CheckCircleIcon className="w-10 h-10 text-success" />
            </div>
            <h1 className="text-h1 text-white mb-4">Account Created!</h1>
            <p className="text-body text-text-secondary mb-8">
              Your account has been created successfully. You can now sign in to access Stratum AI.
            </p>
            <div className="space-y-4">
              <button
                onClick={() => navigate('/login')}
                className="w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body
                           hover:shadow-glow transition-all duration-base"
              >
                Go to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-primary flex mx-auto" style={{ maxWidth: '1500px', width: '100%' }}>
      {/* Left side - Brand */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-stratum-500/20 via-surface-primary to-cyan-500/10" />
        <div className="absolute -top-1/4 -left-1/4 w-[600px] h-[600px] rounded-full bg-stratum-500/20 blur-3xl" />
        <div className="absolute -bottom-1/4 -right-1/4 w-[400px] h-[400px] rounded-full bg-cyan-500/15 blur-3xl" />

        <div className="relative z-10 flex flex-col justify-center p-16">
          <Link to="/" className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 rounded-xl bg-gradient-stratum flex items-center justify-center">
              <span className="text-white font-bold text-h2">S</span>
            </div>
            <span className="text-h1 text-white font-semibold">Stratum AI</span>
          </Link>

          <h2 className="text-[40px] font-bold text-white leading-tight mb-6">
            Start optimizing your{' '}
            <span className="bg-gradient-stratum bg-clip-text text-transparent">
              ad campaigns
            </span>{' '}
            today
          </h2>

          <p className="text-body text-text-secondary max-w-md">
            Join thousands of marketing teams who trust Stratum AI to deliver better ROAS with confidence.
          </p>

          <div className="mt-12 space-y-4">
            {[
              '14-day free trial, no credit card required',
              'Connect Meta, Google, TikTok, Snapchat + GA4',
              'AI-powered recommendations and automation',
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-3">
                <CheckCircleIcon className="w-5 h-5 text-success" />
                <span className="text-body text-text-secondary">{feature}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-16">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-gradient-stratum flex items-center justify-center">
                <span className="text-white font-bold text-h3">S</span>
              </div>
              <span className="text-h2 text-white font-semibold">Stratum AI</span>
            </Link>
          </div>

          <div className="motion-enter">
            <h1 className="text-h1 text-white mb-2">Create your account</h1>
            <p className="text-body text-text-muted mb-8">
              Already have an account?{' '}
              <Link to="/login" className="text-stratum-400 hover:text-stratum-300 transition-colors">
                Sign in
              </Link>
            </p>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* API Error */}
              {apiError && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-danger/10 text-danger">
                  <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                  <span className="text-meta">{apiError}</span>
                </div>
              )}

              {/* Name */}
              <div>
                <label className="block text-meta text-text-secondary mb-2">Full name</label>
                <div className="relative">
                  <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('name')}
                    type="text"
                    placeholder="John Doe"
                    className="w-full pl-12 pr-4 py-3 rounded-xl bg-surface-secondary border border-white/10
                               text-white placeholder-text-muted text-body
                               focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                               transition-all duration-base outline-none"
                  />
                </div>
                {errors.name && (
                  <p className="mt-2 text-meta text-danger">{errors.name.message}</p>
                )}
              </div>

              {/* Email */}
              <div>
                <label className="block text-meta text-text-secondary mb-2">Email address</label>
                <div className="relative">
                  <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="you@company.com"
                    className="w-full pl-12 pr-4 py-3 rounded-xl bg-surface-secondary border border-white/10
                               text-white placeholder-text-muted text-body
                               focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                               transition-all duration-base outline-none"
                  />
                </div>
                {errors.email && (
                  <p className="mt-2 text-meta text-danger">{errors.email.message}</p>
                )}
              </div>

              {/* Phone Number */}
              <div>
                <label className="block text-meta text-text-secondary mb-2">WhatsApp number</label>
                <div className="relative">
                  <PhoneIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('phone')}
                    type="tel"
                    placeholder="+1 234 567 8900"
                    className="w-full pl-12 pr-4 py-3 rounded-xl bg-surface-secondary border border-white/10
                               text-white placeholder-text-muted text-body
                               focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                               transition-all duration-base outline-none"
                  />
                </div>
                <p className="mt-1 text-xs text-text-muted">Include country code for WhatsApp verification</p>
                {errors.phone && (
                  <p className="mt-2 text-meta text-danger">{errors.phone.message}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <label className="block text-meta text-text-secondary mb-2">Password</label>
                <div className="relative">
                  <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    className="w-full pl-12 pr-12 py-3 rounded-xl bg-surface-secondary border border-white/10
                               text-white placeholder-text-muted text-body
                               focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                               transition-all duration-base outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors"
                  >
                    {showPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-2 text-meta text-danger">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-meta text-text-secondary mb-2">Confirm password</label>
                <div className="relative">
                  <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...register('confirmPassword')}
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Confirm your password"
                    className="w-full pl-12 pr-12 py-3 rounded-xl bg-surface-secondary border border-white/10
                               text-white placeholder-text-muted text-body
                               focus:border-stratum-500/50 focus:ring-2 focus:ring-stratum-500/20
                               transition-all duration-base outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors"
                  >
                    {showConfirmPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-2 text-meta text-danger">{errors.confirmPassword.message}</p>
                )}
              </div>

              {/* Terms */}
              <div className="flex items-start gap-3">
                <input
                  {...register('acceptTerms')}
                  type="checkbox"
                  id="terms"
                  className="mt-1 w-4 h-4 rounded border-white/20 bg-surface-secondary
                             text-stratum-500 focus:ring-stratum-500/20 focus:ring-offset-0"
                />
                <label htmlFor="terms" className="text-meta text-text-muted">
                  I agree to the{' '}
                  <a href="/terms" className="text-stratum-400 hover:text-stratum-300">Terms of Service</a>
                  {' '}and{' '}
                  <a href="/privacy" className="text-stratum-400 hover:text-stratum-300">Privacy Policy</a>
                </label>
              </div>
              {errors.acceptTerms && (
                <p className="text-meta text-danger">{errors.acceptTerms.message}</p>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body
                           hover:shadow-glow transition-all duration-base
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Creating account...
                  </span>
                ) : (
                  'Create account'
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 bg-surface-primary text-meta text-text-muted">Or continue with</span>
              </div>
            </div>

            {/* Social login */}
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                className="flex items-center justify-center gap-2 py-3 rounded-xl bg-surface-secondary border border-white/10
                           text-white text-meta font-medium hover:bg-surface-tertiary transition-colors"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Google
              </button>
              <button
                type="button"
                className="flex items-center justify-center gap-2 py-3 rounded-xl bg-surface-secondary border border-white/10
                           text-white text-meta font-medium hover:bg-surface-tertiary transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                Microsoft
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
