import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  FingerPrintIcon,
} from '@heroicons/react/24/outline';
import { useForgotPassword } from '@/api/auth';
import { SEO } from '@/components/common/SEO';
import { authStyles } from '@/components/auth/authStyles';

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
        <style>{authStyles}</style>
        <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
          <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
            <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 215, 0, 0.05), transparent 60%)' }} />
          </div>

          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircleIcon className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                Transmission Sent
              </h2>
              <p className="text-slate-400 text-sm mb-2">
                We've transmitted a key reset link to:
              </p>
              <p className="text-[#FF8C00] font-mono text-sm font-bold mb-8">
                {submittedEmail}
              </p>
              <p className="text-[10px] text-slate-600 font-mono mb-8">
                If you don't see it in your inbox, check your spam folder.
              </p>
              <div className="space-y-4">
                <Link
                  to="/login"
                  className="block w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center transition-all active:scale-[0.98]"
                >
                  BACK TO SESSION
                </Link>
                <button
                  onClick={() => forgotPasswordMutation.reset()}
                  className="text-xs text-[#FF1F6D] hover:text-white transition-colors font-bold uppercase tracking-widest"
                >
                  Try different identifier
                </button>
              </div>
            </div>
          </main>
        </div>
      </>
    );
  }

  return (
    <>
      <SEO title="Forgot Password" description="Reset your Stratum AI account password." noIndex url="https://stratum-ai.com/forgot-password" />
      <style>{authStyles}</style>

      <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
        </div>

        <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
          <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up">
            {/* Back link */}
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono mb-8"
            >
              &larr; Back to session
            </Link>

            {/* Header */}
            <div className="mb-8">
              <h2 className="text-2xl font-display font-extrabold text-white mb-2 tracking-tight">
                Reset Security Key
              </h2>
              <p className="text-slate-400 text-sm">
                Enter your neural identifier and we'll transmit a reset link.
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

              {/* Email */}
              <div className="space-y-2 auth-fade-up-d1">
                <label
                  htmlFor="forgot-email"
                  className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                >
                  Neural Identifier
                </label>
                <div className="relative">
                  <FingerPrintIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                  <input
                    {...register('email')}
                    id="forgot-email"
                    type="email"
                    placeholder="u_alpha_772"
                    className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-4 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.3)]"
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
                className="auth-fade-up-d2 w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    TRANSMITTING...
                  </span>
                ) : (
                  <>TRANSMIT RESET LINK</>
                )}
              </button>
            </form>

            {/* Footer */}
            <div className="mt-8 text-center">
              <p className="text-[13px] text-white/30">
                Remember your key?{' '}
                <Link to="/login" className="text-[#FF1F6D] font-bold hover:text-white transition-colors">
                  Initialize session
                </Link>
              </p>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
