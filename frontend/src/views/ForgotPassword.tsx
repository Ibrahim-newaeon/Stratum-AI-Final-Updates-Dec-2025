import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { CheckCircle, AlertCircle, Mail, ArrowLeft } from 'lucide-react';
import { useForgotPassword } from '@/api/auth';
import { SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

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
      <>
        <SEO title="Forgot Password" description="Reset your Stratum AI account password." noIndex url="https://stratum-ai.com/forgot-password" />
        <div className="min-h-screen flex bg-background text-foreground font-sans">
          <AuthLeftPanel />
          <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
            <div className="w-full max-w-md bg-card border border-border rounded-xl p-8 shadow-xl text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-2xl font-semibold text-foreground mb-2">
                Check your email
              </h2>
              <p className="text-sm text-muted-foreground mb-2">
                We've sent a password reset link to:
              </p>
              <p className="text-secondary text-sm font-semibold mb-8">
                {submittedEmail}
              </p>
              <p className="text-xs text-muted-foreground mb-8">
                If you don't see it in your inbox, check your spam folder.
              </p>
              <div className="space-y-4">
                <Link
                  to="/login"
                  className="block w-full bg-gradient-to-r from-primary to-secondary text-background font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 text-center"
                >
                  Back to login
                </Link>
                <button
                  onClick={() => forgotPasswordMutation.reset()}
                  className="text-xs text-muted-foreground hover:text-secondary transition-colors duration-200 font-medium"
                >
                  Try a different email
                </button>
              </div>
            </div>
          </section>
        </div>
      </>
    );
  }

  return (
    <>
      <SEO title="Forgot Password" description="Reset your Stratum AI account password." noIndex url="https://stratum-ai.com/forgot-password" />

      <div className="min-h-screen flex bg-background text-foreground font-sans">
        <AuthLeftPanel />

        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          <div className="w-full max-w-md bg-card border border-border rounded-xl p-8 shadow-xl">
            {/* Back link */}
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-secondary transition-colors duration-200 font-medium mb-8"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to login
            </Link>

            {/* Header */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-foreground mb-2">
                Reset your password
              </h2>
              <p className="text-sm text-muted-foreground">
                Enter your email and we'll send you a reset link.
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

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="forgot-email" className="text-xs font-medium text-muted-foreground ml-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
                  <input
                    {...register('email')}
                    id="forgot-email"
                    type="email"
                    placeholder="you@company.com"
                    className="w-full bg-muted border border-border rounded-lg pl-11 pr-4 py-3 text-sm text-foreground placeholder-muted-foreground outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary/50 transition-colors duration-200"
                  />
                </div>
                {errors.email && (
                  <p className="text-xs text-red-400 mt-1 ml-1">{errors.email.message}</p>
                )}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-primary to-secondary text-background font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Sending...
                  </span>
                ) : (
                  'Send reset link'
                )}
              </button>
            </form>

            {/* Footer */}
            <div className="mt-8 text-center">
              <p className="text-sm text-muted-foreground">
                Remember your password?{' '}
                <Link to="/login" className="text-secondary hover:text-secondary transition-colors duration-200 font-medium">
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
