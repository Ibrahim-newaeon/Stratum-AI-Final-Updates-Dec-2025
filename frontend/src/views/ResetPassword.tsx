import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  LockClosedIcon,
  ArrowLeftIcon,
  CheckCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useResetPassword } from '@/api/auth';

const resetPasswordSchema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const resetPasswordMutation = useResetPassword();

  const isLoading = resetPasswordMutation.isPending;
  const isSuccess = resetPasswordMutation.isSuccess;
  const apiError = resetPasswordMutation.error?.message;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  });

  // If no token, show error
  if (!token) {
    return (
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            <div className="w-20 h-20 rounded-full bg-danger/10 flex items-center justify-center mx-auto mb-6">
              <ExclamationTriangleIcon className="w-10 h-10 text-danger" />
            </div>
            <h1 className="text-h1 text-white mb-4">Invalid reset link</h1>
            <p className="text-body text-text-secondary mb-8">
              This password reset link is invalid or has expired. Please request a new one.
            </p>
            <Link
              to="/forgot-password"
              className="inline-block w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body text-center
                         hover:shadow-glow transition-all duration-base"
            >
              Request new link
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const onSubmit = async (data: ResetPasswordForm) => {
    resetPasswordMutation.mutate({ token, password: data.password });
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <div className="motion-enter">
            <div className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-6">
              <CheckCircleIcon className="w-10 h-10 text-success" />
            </div>
            <h1 className="text-h1 text-white mb-4">Password reset successful</h1>
            <p className="text-body text-text-secondary mb-8">
              Your password has been reset. You can now sign in with your new password.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="w-full py-3 rounded-xl bg-gradient-stratum text-white font-medium text-body
                         hover:shadow-glow transition-all duration-base"
            >
              Sign in
            </button>
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

          <h1 className="text-h1 text-white mb-2">Reset your password</h1>
          <p className="text-body text-text-muted mb-8">
            Enter your new password below.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* API Error */}
            {apiError && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-danger/10 text-danger">
                <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                <span className="text-meta">{apiError}</span>
              </div>
            )}

            {/* Password */}
            <div>
              <label className="block text-meta text-text-secondary mb-2">New password</label>
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
              <label className="block text-meta text-text-secondary mb-2">Confirm new password</label>
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
                  Resetting password...
                </span>
              ) : (
                'Reset password'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
