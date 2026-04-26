import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  LockClosedIcon,
  CheckCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useResetPassword } from '@/api/auth';
import { authStyles } from '@/components/auth/authStyles';

const resetPasswordSchema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

/** Shared background with floating orbs and cyber grid */
function AuthBackground() {
  return (
    <>
      <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
        <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
        <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 215, 0, 0.05), transparent 60%)' }} />
      </div>
    </>
  );
}

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
      <>
        <style>{authStyles}</style>
        <div className="dark bg-background text-foreground min-h-screen flex font-sans selection:bg-primary/30 overflow-hidden">
          <AuthBackground />
          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 dark:border-white/10 border-border/50 relative z-10 shadow-2xl auth-fade-up text-center">
              <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
                <ExclamationTriangleIcon className="w-8 h-8 text-red-400" />
              </div>
              <h2 className="text-2xl font-display font-extrabold text-foreground mb-2 tracking-tight">
                Invalid Reset Link
              </h2>
              <p className="text-muted-foreground text-sm mb-8">
                This security key reset link is invalid or has expired. Request a new transmission.
              </p>
              <Link
                to="/forgot-password"
                className="block w-full auth-gradient-btn auth-shimmer-btn text-foreground font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center transition-colors active:scale-[0.98]"
              >
                REQUEST NEW LINK
              </Link>
            </div>
          </main>
        </div>
      </>
    );
  }

  const onSubmit = async (data: ResetPasswordForm) => {
    resetPasswordMutation.mutate({ token, password: data.password });
  };

  // Success state
  if (isSuccess) {
    return (
      <>
        <style>{authStyles}</style>
        <div className="dark bg-background text-foreground min-h-screen flex font-sans selection:bg-primary/30 overflow-hidden">
          <AuthBackground />
          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 dark:border-white/10 border-border/50 relative z-10 shadow-2xl auth-fade-up text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircleIcon className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-2xl font-display font-extrabold text-foreground mb-2 tracking-tight">
                Key Reset Complete
              </h2>
              <p className="text-muted-foreground text-sm mb-8">
                Your security key has been updated. Initialize your session with the new credentials.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full auth-gradient-btn auth-shimmer-btn text-foreground font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center transition-colors active:scale-[0.98]"
              >
                INITIALIZE SESSION
              </button>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Form state
  return (
    <>
      <style>{authStyles}</style>
      <div className="dark bg-background text-foreground min-h-screen flex font-sans selection:bg-primary/30 overflow-hidden">
        <AuthBackground />

        <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
          <div className="w-full max-w-md auth-glass-card rounded-xl p-10 dark:border-white/10 border-border/50 relative z-10 shadow-2xl auth-fade-up">
            {/* Back link */}
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-[10px] text-muted-foreground hover:text-foreground transition-colors uppercase tracking-widest mb-8"
            >
              &larr; Back to session
            </Link>

            {/* Header */}
            <div className="mb-8">
              <h2 className="text-2xl font-display font-extrabold text-foreground mb-2 tracking-tight">
                Reset Security Key
              </h2>
              <p className="text-muted-foreground text-sm">
                Enter your new security key below.
              </p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* API Error */}
              {apiError && (
                <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400">
                  <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                  <span>{apiError}</span>
                </div>
              )}

              {/* New Password */}
              <div className="space-y-2 auth-fade-up-d1">
                <label
                  htmlFor="reset-password"
                  className="text-[10px] uppercase font-bold tracking-[0.15em] text-muted-foreground ml-1"
                >
                  New Security Key
                </label>
                <div className="relative">
                  <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
                  <input
                    {...register('password')}
                    id="reset-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    className="w-full h-11 bg-background/80 border dark:border-white/10 border-border/50 rounded-[12px] pl-12 pr-11 text-foreground text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary "
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-foreground/25 hover:text-muted-foreground transition-colors"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2 auth-fade-up-d2">
                <label
                  htmlFor="reset-confirm-password"
                  className="text-[10px] uppercase font-bold tracking-[0.15em] text-muted-foreground ml-1"
                >
                  Confirm Security Key
                </label>
                <div className="relative">
                  <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
                  <input
                    {...register('confirmPassword')}
                    id="reset-confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Re-enter security key"
                    className="w-full h-11 bg-background/80 border dark:border-white/10 border-border/50 rounded-[12px] pl-12 pr-11 text-foreground text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary "
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-foreground/25 hover:text-muted-foreground transition-colors"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
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
                className="auth-fade-up-d3 w-full auth-gradient-btn auth-shimmer-btn text-foreground font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-colors active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    RESETTING...
                  </span>
                ) : (
                  <>RESET SECURITY KEY</>
                )}
              </button>
            </form>
          </div>
        </main>
      </div>
    </>
  );
}


