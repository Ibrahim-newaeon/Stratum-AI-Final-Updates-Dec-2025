import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Lock, CheckCircle, Eye, EyeOff, AlertTriangle, AlertCircle } from 'lucide-react';
import { useResetPassword } from '@/api/auth';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

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

  // No token — invalid link
  if (!token) {
    return (
      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />
        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
              Invalid reset link
            </h2>
            <p className="text-sm text-[#8B92A8] mb-8">
              This password reset link is invalid or has expired. Request a new link.
            </p>
            <Link
              to="/forgot-password"
              className="block w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 text-center"
            >
              Request new link
            </Link>
          </div>
        </section>
      </div>
    );
  }

  const onSubmit = async (data: ResetPasswordForm) => {
    resetPasswordMutation.mutate({ token, password: data.password });
  };

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />
        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
              Password reset complete
            </h2>
            <p className="text-sm text-[#8B92A8] mb-8">
              Your password has been updated. Sign in with your new credentials.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200"
            >
              Sign in
            </button>
          </div>
        </section>
      </div>
    );
  }

  // Form state
  return (
    <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
      <AuthLeftPanel />

      <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
        <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
          {/* Header */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
              Set new password
            </h2>
            <p className="text-sm text-[#8B92A8]">
              Enter your new password below.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* API Error */}
            {apiError && (
              <div className="flex items-center gap-2 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            {/* New Password */}
            <div className="space-y-2">
              <label htmlFor="reset-password" className="text-xs font-medium text-[#8B92A8] ml-1">
                New password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                <input
                  {...register('password')}
                  id="reset-password"
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
              <label htmlFor="reset-confirm-password" className="text-xs font-medium text-[#8B92A8] ml-1">
                Confirm password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                <input
                  {...register('confirmPassword')}
                  id="reset-confirm-password"
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
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="text-xs text-red-400 mt-1 ml-1">{errors.confirmPassword.message}</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Resetting...
                </span>
              ) : (
                'Reset password'
              )}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
