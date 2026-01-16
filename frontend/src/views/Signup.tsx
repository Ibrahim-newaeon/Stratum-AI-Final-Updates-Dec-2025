/**
 * Signup Page
 * User registration for Stratum AI
 * Theme: Infobip-inspired dark design matching landing.html
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  EyeIcon,
  EyeSlashIcon,
  EnvelopeIcon,
  LockClosedIcon,
  UserIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  PhoneIcon,
} from '@heroicons/react/24/outline';
import { useSignup, useResendVerification, useSendWhatsAppOTP, useVerifyWhatsAppOTP } from '@/api/auth';
import { OTPInput } from '@/components/ui/otp-input';
import { PhoneInput } from '@/components/ui/phone-input';

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

// Shared styles
const inputStyle = {
  background: 'rgba(255, 255, 255, 0.06)',
  border: '1px solid rgba(255, 255, 255, 0.12)'
};

const cardStyle = {
  background: 'rgba(255, 255, 255, 0.04)',
  border: '1px solid rgba(255, 255, 255, 0.12)',
  backdropFilter: 'blur(20px)'
};

export default function Signup() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [, setSubmittedEmail] = useState('');
  const [step, setStep] = useState<SignupStep>('details');
  const [formData, setFormData] = useState<SignupForm | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [_verificationToken, setVerificationToken] = useState('');
  const [otpError, setOtpError] = useState('');
  const [otpCountdown, setOtpCountdown] = useState(0);

  const signupMutation = useSignup();
  useResendVerification();
  const sendOTPMutation = useSendWhatsAppOTP();
  const verifyOTPMutation = useVerifyWhatsAppOTP();

  const isLoading = signupMutation.isPending || sendOTPMutation.isPending;
  const isSuccess = signupMutation.isSuccess;
  const apiError = signupMutation.error?.message || sendOTPMutation.error?.message;

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { phone: '+1 ' },
  });

  const startOTPCountdown = () => {
    setOtpCountdown(60);
    const timer = setInterval(() => {
      setOtpCountdown((prev) => {
        if (prev <= 1) { clearInterval(timer); return 0; }
        return prev - 1;
      });
    }, 1000);
  };

  const onSubmit = async (data: SignupForm) => {
    setFormData(data);
    setSubmittedEmail(data.email);
    sendOTPMutation.mutate(
      { phone_number: data.phone },
      { onSuccess: () => { setStep('verify-phone'); startOTPCountdown(); } }
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
          const token = response.verification_token || '';
          setVerificationToken(token);
          signupMutation.mutate({
            name: formData.name,
            email: formData.email,
            password: formData.password,
            phone: formData.phone,
            verification_token: token,
          });
        },
        onError: (error) => setOtpError(error.message || 'Invalid OTP code'),
      }
    );
  };

  const handleResendOTP = () => {
    if (formData && otpCountdown === 0) {
      sendOTPMutation.mutate(
        { phone_number: formData.phone },
        { onSuccess: () => { startOTPCountdown(); setOtpCode(''); setOtpError(''); } }
      );
    }
  };

  // Background orbs component
  const BackgroundOrbs = () => (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div
        className="absolute w-[600px] h-[600px] rounded-full blur-[80px] opacity-50 animate-[orbFloat_15s_ease-in-out_infinite]"
        style={{ background: 'rgba(252, 100, 35, 0.25)', top: '-200px', left: '-200px' }}
      />
      <div
        className="absolute w-[500px] h-[500px] rounded-full blur-[80px] opacity-50 animate-[orbFloat_15s_ease-in-out_infinite]"
        style={{ background: 'rgba(57, 128, 234, 0.25)', bottom: '-150px', right: '-150px', animationDelay: '-5s' }}
      />
      <div
        className="absolute w-[400px] h-[400px] rounded-full blur-[80px] opacity-40 animate-[orbFloat_15s_ease-in-out_infinite]"
        style={{ background: 'rgba(150, 112, 194, 0.18)', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', animationDelay: '-10s' }}
      />
    </div>
  );

  // CSS for animations
  const animationStyles = `
    @keyframes orbFloat {
      0%, 100% { transform: translate(0, 0) scale(1); }
      25% { transform: translate(50px, -50px) scale(1.1); }
      50% { transform: translate(-30px, 30px) scale(0.95); }
      75% { transform: translate(30px, 50px) scale(1.05); }
    }
  `;

  // OTP Verification Step
  if (step === 'verify-phone') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: '#0C1B2C' }}>
        <BackgroundOrbs />
        <style>{animationStyles}</style>
        <div className="max-w-md w-full relative z-10">
          <div className="p-8 rounded-2xl text-center" style={cardStyle}>
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: 'rgba(252, 100, 35, 0.1)' }}
            >
              <PhoneIcon className="w-10 h-10" style={{ color: '#FC6423' }} />
            </div>
            <h1 className="text-2xl font-bold text-white mb-4">Verify your WhatsApp</h1>
            <p className="text-sm mb-2" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              We've sent a 6-digit code to your WhatsApp
            </p>
            <p className="font-medium mb-8" style={{ color: '#FC6423' }}>
              {formData?.phone}
            </p>

            <div className="mb-6">
              <OTPInput
                value={otpCode}
                onChange={(value) => { setOtpCode(value); setOtpError(''); }}
                error={!!otpError}
                disabled={verifyOTPMutation.isPending}
              />
              {otpError && (
                <p className="mt-3 text-sm text-center" style={{ color: '#ef4444' }}>{otpError}</p>
              )}
            </div>

            <div className="space-y-4">
              <button
                onClick={handleVerifyOTP}
                disabled={verifyOTPMutation.isPending || otpCode.length !== 6}
                className="w-full py-3.5 rounded-xl font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: '#FC6423', boxShadow: '0 4px 20px rgba(252, 100, 35, 0.4)' }}
              >
                {verifyOTPMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Verifying...
                  </span>
                ) : 'Verify & Create Account'}
              </button>

              <button
                onClick={handleResendOTP}
                disabled={otpCountdown > 0 || sendOTPMutation.isPending}
                className="text-sm transition-colors disabled:opacity-50"
                style={{ color: '#FC6423' }}
              >
                {sendOTPMutation.isPending ? 'Sending...' : otpCountdown > 0 ? `Resend code in ${otpCountdown}s` : 'Resend code'}
              </button>

              <button
                onClick={() => setStep('details')}
                className="block w-full text-sm transition-colors"
                style={{ color: 'rgba(255, 255, 255, 0.5)' }}
              >
                Back to signup
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Success Step
  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: '#0C1B2C' }}>
        <BackgroundOrbs />
        <style>{animationStyles}</style>
        <div className="max-w-md w-full relative z-10">
          <div className="p-8 rounded-2xl text-center" style={cardStyle}>
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: 'rgba(109, 207, 167, 0.1)' }}
            >
              <CheckCircleIcon className="w-10 h-10" style={{ color: '#6DCFA7' }} />
            </div>
            <h1 className="text-2xl font-bold text-white mb-4">Account Created!</h1>
            <p className="text-sm mb-4" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              Your account has been created successfully.
            </p>

            <div className="mb-8 p-4 rounded-xl" style={{ background: 'rgba(252, 100, 35, 0.1)', border: '1px solid rgba(252, 100, 35, 0.2)' }}>
              <div className="flex items-center justify-center gap-2 mb-2">
                <EnvelopeIcon className="w-5 h-5" style={{ color: '#FC6423' }} />
                <span className="font-medium" style={{ color: '#FC6423' }}>Verify your email</span>
              </div>
              <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                We've sent a verification link to <span className="text-white">{formData?.email}</span>.
                Please check your inbox.
              </p>
            </div>

            <div className="space-y-4">
              <button
                onClick={() => navigate('/login')}
                className="w-full py-3.5 rounded-xl font-semibold text-white transition-all"
                style={{ background: '#FC6423', boxShadow: '0 4px 20px rgba(252, 100, 35, 0.4)' }}
              >
                Go to Login
              </button>
              <p className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>
                Didn't receive the email?{' '}
                <button
                  onClick={() => navigate(`/verify-email?email=${encodeURIComponent(formData?.email || '')}`)}
                  style={{ color: '#FC6423' }}
                >
                  Resend verification
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Main Signup Form
  return (
    <div className="min-h-screen flex" style={{ background: '#0C1B2C' }}>
      <BackgroundOrbs />
      <style>{animationStyles}</style>

      {/* Left side - Brand */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, rgba(252, 100, 35, 0.1) 0%, rgba(57, 128, 234, 0.1) 100%)' }} />

        <div className="relative z-10 flex flex-col justify-between p-12 text-white w-full">
          <div>
            <Link to="/" className="flex items-center gap-3 mb-12">
              <div className="h-12 w-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #FC6423 0%, #3980EA 100%)' }}>
                <span className="text-white font-bold text-2xl">S</span>
              </div>
              <span className="text-3xl font-bold" style={{ background: 'linear-gradient(135deg, #FC6423 0%, #3980EA 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Stratum AI
              </span>
            </Link>

            <h1 className="text-4xl font-bold mb-4 leading-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Start optimizing your
              <br />
              <span style={{ color: '#FC6423' }}>ad campaigns today</span>
            </h1>
            <p className="text-lg max-w-md" style={{ color: 'rgba(255, 255, 255, 0.75)' }}>
              Join thousands of marketing teams who trust Stratum AI to deliver better ROAS with confidence.
            </p>
          </div>

          {/* Features */}
          <div className="space-y-4 mt-12">
            {[
              '14-day free trial, no credit card required',
              'Connect Meta, Google, TikTok, Snapchat + GA4',
              'AI-powered recommendations and automation',
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-3">
                <CheckCircleIcon className="w-5 h-5" style={{ color: '#6DCFA7' }} />
                <span style={{ color: 'rgba(255, 255, 255, 0.75)' }}>{feature}</span>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-6 mt-12">
            {[
              { value: '150+', label: 'Growth Teams' },
              { value: '$12M+', label: 'Revenue Recovered' },
              { value: '4.2x', label: 'Avg ROAS Lift' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl font-bold" style={{ color: '#FC6423' }}>{stat.value}</div>
                <div className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 relative z-10">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #FC6423 0%, #3980EA 100%)' }}>
                <span className="text-white font-bold text-xl">S</span>
              </div>
              <span className="text-2xl font-bold" style={{ background: 'linear-gradient(135deg, #FC6423 0%, #3980EA 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                Stratum AI
              </span>
            </Link>
          </div>

          {/* Card */}
          <div className="p-8 rounded-2xl" style={cardStyle}>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">Create your account</h2>
              <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                Already have an account?{' '}
                <Link to="/login" className="font-medium hover:underline" style={{ color: '#FC6423' }}>Sign in</Link>
              </p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {apiError && (
                <div className="flex items-center gap-2 p-3 rounded-lg text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
                  <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                  <span>{apiError}</span>
                </div>
              )}

              {/* Name */}
              <div>
                <label className="text-sm font-medium text-white block mb-2">Full name</label>
                <div className="relative">
                  <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'rgba(255, 255, 255, 0.5)' }} />
                  <input
                    {...register('name')}
                    type="text"
                    placeholder="John Doe"
                    className="w-full pl-12 pr-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all"
                    style={inputStyle}
                    onFocus={(e) => e.target.style.borderColor = '#FC6423'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)'}
                  />
                </div>
                {errors.name && <p className="mt-1 text-sm" style={{ color: '#ef4444' }}>{errors.name.message}</p>}
              </div>

              {/* Email */}
              <div>
                <label className="text-sm font-medium text-white block mb-2">Email address</label>
                <div className="relative">
                  <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'rgba(255, 255, 255, 0.5)' }} />
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="you@company.com"
                    className="w-full pl-12 pr-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all"
                    style={inputStyle}
                    onFocus={(e) => e.target.style.borderColor = '#FC6423'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)'}
                  />
                </div>
                {errors.email && <p className="mt-1 text-sm" style={{ color: '#ef4444' }}>{errors.email.message}</p>}
              </div>

              {/* Phone */}
              <div>
                <label className="text-sm font-medium text-white block mb-2">WhatsApp number</label>
                <Controller
                  name="phone"
                  control={control}
                  render={({ field }) => (
                    <PhoneInput value={field.value} onChange={field.onChange} error={!!errors.phone} placeholder="234 567 8900" />
                  )}
                />
                <p className="mt-1 text-xs" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>We'll send a verification code to your WhatsApp</p>
                {errors.phone && <p className="mt-1 text-sm" style={{ color: '#ef4444' }}>{errors.phone.message}</p>}
              </div>

              {/* Password */}
              <div>
                <label className="text-sm font-medium text-white block mb-2">Password</label>
                <div className="relative">
                  <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'rgba(255, 255, 255, 0.5)' }} />
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    className="w-full pl-12 pr-12 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all"
                    style={inputStyle}
                    onFocus={(e) => e.target.style.borderColor = '#FC6423'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)'}
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 hover:text-white transition-colors" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    {showPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && <p className="mt-1 text-sm" style={{ color: '#ef4444' }}>{errors.password.message}</p>}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="text-sm font-medium text-white block mb-2">Confirm password</label>
                <div className="relative">
                  <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'rgba(255, 255, 255, 0.5)' }} />
                  <input
                    {...register('confirmPassword')}
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Confirm your password"
                    className="w-full pl-12 pr-12 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all"
                    style={inputStyle}
                    onFocus={(e) => e.target.style.borderColor = '#FC6423'}
                    onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)'}
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 hover:text-white transition-colors" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    {showConfirmPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
                {errors.confirmPassword && <p className="mt-1 text-sm" style={{ color: '#ef4444' }}>{errors.confirmPassword.message}</p>}
              </div>

              {/* Terms */}
              <div className="flex items-start gap-3">
                <input {...register('acceptTerms')} type="checkbox" id="terms" className="mt-1 w-4 h-4 rounded" style={{ accentColor: '#FC6423' }} />
                <label htmlFor="terms" className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  I agree to the{' '}
                  <a href="/terms" style={{ color: '#FC6423' }}>Terms of Service</a>
                  {' '}and{' '}
                  <a href="/privacy" style={{ color: '#FC6423' }}>Privacy Policy</a>
                </label>
              </div>
              {errors.acceptTerms && <p className="text-sm" style={{ color: '#ef4444' }}>{errors.acceptTerms.message}</p>}

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 rounded-xl font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: '#FC6423', boxShadow: '0 4px 20px rgba(252, 100, 35, 0.4)' }}
                onMouseOver={(e) => { if (!isLoading) { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 30px rgba(252, 100, 35, 0.5)'; } }}
                onMouseOut={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(252, 100, 35, 0.4)'; }}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Creating account...
                  </span>
                ) : 'Create account'}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.12)' }} />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 text-sm" style={{ background: 'rgba(12, 27, 44, 0.8)', color: 'rgba(255, 255, 255, 0.5)' }}>Or continue with</span>
              </div>
            </div>

            {/* Social login */}
            <div className="grid grid-cols-2 gap-3">
              <button type="button" className="flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-medium transition-all hover:bg-white/10" style={inputStyle}>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Google
              </button>
              <button type="button" className="flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-medium transition-all hover:bg-white/10" style={inputStyle}>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                Microsoft
              </button>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-xs mt-6" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>
            By creating an account, you agree to our{' '}
            <a href="#" className="hover:underline" style={{ color: '#FC6423' }}>Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="hover:underline" style={{ color: '#FC6423' }}>Privacy Policy</a>
          </p>
        </div>
      </div>
    </div>
  );
}
