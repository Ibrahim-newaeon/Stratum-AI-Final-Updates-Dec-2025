/**
 * Forgot Password Page - Stratum HoloGlass Theme
 * Deep black background (#0b1215) + gold accent
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useForgotPassword } from '@/api/auth';

// Stratum HoloGlass Theme
const theme = {
  primary: '#00c7be',
  primaryHover: '#c49a2c',
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  bgBase: '#0b1215',
  bgElevated: 'rgba(255, 255, 255, 0.05)',
  bgSurface: 'rgba(255, 255, 255, 0.03)',
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.08)',
  success: '#34c759',
};

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email'),
});

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPassword() {
  const [submittedEmail, setSubmittedEmail] = useState('');
  const forgotPasswordMutation = useForgotPassword();

  const isLoading = forgotPasswordMutation.isPending;
  const isSuccess = forgotPasswordMutation.isSuccess;
  const apiError = forgotPasswordMutation.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordForm) => {
    setSubmittedEmail(data.email);
    forgotPasswordMutation.mutate({ email: data.email });
  };

  if (isSuccess) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: theme.bgElevated }}
      >
        <div className="max-w-md w-full text-center">
          <div
            className="p-8 rounded-2xl"
            style={{
              background: theme.bgSurface,
              border: `1px solid ${theme.border}`,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            }}
          >
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: `${theme.success}15` }}
            >
              <CheckCircleIcon className="w-8 h-8" style={{ color: theme.success }} />
            </div>
            <h1 className="text-2xl font-semibold mb-3" style={{ color: theme.textPrimary }}>
              Check your email
            </h1>
            <p className="mb-2" style={{ color: theme.textMuted }}>
              We've sent a password reset link to:
            </p>
            <p className="font-medium mb-6" style={{ color: theme.textPrimary }}>
              {submittedEmail}
            </p>
            <p className="text-sm mb-6" style={{ color: theme.textMuted }}>
              If you don't see it in your inbox, check your spam folder.
            </p>
            <Link
              to="/login"
              className="block w-full py-3 rounded-xl text-black font-semibold text-center transition-all duration-200"
              style={{ background: theme.primary }}
              onMouseEnter={(e) => (e.currentTarget.style.background = theme.primaryHover)}
              onMouseLeave={(e) => (e.currentTarget.style.background = theme.primary)}
            >
              Back to Login
            </Link>
            <button
              onClick={() => forgotPasswordMutation.reset()}
              className="mt-4 text-sm font-medium transition-colors hover:underline"
              style={{ color: theme.primary }}
            >
              Try a different email
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ background: theme.bgElevated }}
    >
      <div className="max-w-md w-full">
        <Link
          to="/login"
          className="inline-flex items-center gap-2 text-sm transition-colors mb-8 hover:underline"
          style={{ color: theme.textMuted }}
        >
          <ArrowLeftIcon className="w-4 h-4" />
          Back to login
        </Link>

        <Link to="/" className="flex items-center gap-3 mb-8">
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center"
            style={{ background: theme.primary }}
          >
            <span className="text-white font-semibold text-lg">S</span>
          </div>
          <span className="text-xl font-semibold" style={{ color: theme.textPrimary }}>
            Stratum AI
          </span>
        </Link>

        <div
          className="p-8 rounded-2xl"
          style={{
            background: theme.bgSurface,
            border: `1px solid ${theme.border}`,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
          }}
        >
          <h1 className="text-2xl font-semibold mb-2" style={{ color: theme.textPrimary }}>
            Forgot your password?
          </h1>
          <p className="mb-6" style={{ color: theme.textMuted }}>
            Enter your email and we'll send you a reset link.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {apiError && (
              <div
                className="flex items-center gap-3 p-4 rounded-xl text-sm"
                style={{
                  background: '#FEF2F2',
                  border: '1px solid #FEE2E2',
                  color: '#DC2626',
                }}
              >
                <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                Email address
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
                  className="w-full pl-12 pr-4 py-3 rounded-xl outline-none transition-all duration-200"
                  style={{
                    background: theme.bgElevated,
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

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl font-semibold text-black transition-all duration-200 disabled:opacity-50"
              style={{ background: theme.primary }}
              onMouseEnter={(e) => {
                if (!isLoading) e.currentTarget.style.background = theme.primaryHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = theme.primary;
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
                  Sending...
                </span>
              ) : (
                'Send reset link'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
