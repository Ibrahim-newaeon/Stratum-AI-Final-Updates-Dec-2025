import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  EnvelopeIcon,
  ArrowLeftIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useForgotPassword } from '@/api/auth';

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
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            <div className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-6">
              <CheckCircleIcon className="w-10 h-10 text-success" />
            </div>
            <h1 className="text-h1 text-white mb-4">Check your email</h1>
            <p className="text-body text-text-secondary mb-2">
              We've sent a password reset link to:
            </p>
            <p className="text-body text-white font-medium mb-8">
              {submittedEmail}
            </p>
            <p className="text-meta text-text-muted mb-8">
              If you don't see it in your inbox, check your spam folder.
            </p>
            <div className="space-y-4">
              <Link
                to="/login"
                className="block w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body text-center
                           hover:shadow-glow transition-all duration-base"
              >
                Back to Login
              </Link>
              <button
                onClick={() => forgotPasswordMutation.reset()}
                className="text-meta text-stratum-400 hover:text-stratum-300 transition-colors"
              >
                Try a different email
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <div className="motion-enter">
          {/* Back link */}
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-meta text-text-muted hover:text-white transition-colors mb-8"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to login
          </Link>

          {/* Logo */}
          <div className="flex items-center gap-2 mb-8">
            <div className="w-10 h-10 rounded-lg bg-gradient-stratum flex items-center justify-center">
              <span className="text-white font-bold text-h3">S</span>
            </div>
            <span className="text-h2 text-white font-semibold">Stratum AI</span>
          </div>

          <h1 className="text-h1 text-white mb-2">Forgot your password?</h1>
          <p className="text-body text-text-muted mb-8">
            No worries! Enter your email address and we'll send you a link to reset your password.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* API Error */}
            {apiError && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-danger/10 text-danger">
                <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                <span className="text-meta">{apiError}</span>
              </div>
            )}

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
                  Sending reset link...
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
