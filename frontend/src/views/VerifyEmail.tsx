import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useVerifyEmail, useResendVerification } from '@/api/auth';
import { authStyles } from '@/components/auth/authStyles';

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

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const verifyMutation = useVerifyEmail();
  const resendMutation = useResendVerification();
  const [resendEmail, setResendEmail] = useState(searchParams.get('email') || '');
  const [showResendForm, setShowResendForm] = useState(false);

  const isLoading = verifyMutation.isPending;
  const isSuccess = verifyMutation.isSuccess;
  const error = verifyMutation.error?.message ||
    (verifyMutation.isError ? 'Verification failed' : '');

  useEffect(() => {
    if (token && !verifyMutation.isPending && !verifyMutation.isSuccess && !verifyMutation.isError) {
      verifyMutation.mutate({ token });
    }
  }, [token]);

  // No token provided
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
                Invalid Verification Link
              </h2>
              <p className="text-muted-foreground text-sm mb-8">
                The verification link is missing or invalid. Check your transmission inbox for the correct link.
              </p>
              <Link
                to="/login"
                className="block w-full auth-gradient-btn auth-shimmer-btn text-foreground font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center transition-colors active:scale-[0.98]"
              >
                BACK TO SESSION
              </Link>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <>
        <style>{authStyles}</style>
        <div className="dark bg-background text-foreground min-h-screen flex font-sans selection:bg-primary/30 overflow-hidden">
          <AuthBackground />
          <main className="relative z-10 w-full flex items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 dark:border-white/10 border-border/50 relative z-10 shadow-2xl auth-fade-up text-center">
              {/* Loading spinner */}
              <div className="w-16 h-16 rounded-full border-4 border-primary/20 border-t-primary animate-spin mx-auto mb-6" />
              <h2 className="text-2xl font-display font-extrabold text-foreground mb-2 tracking-tight">
                Verifying Identity
              </h2>
              <p className="text-muted-foreground text-sm">
                Please wait while we verify your neural identifier...
              </p>
            </div>
          </main>
        </div>
      </>
    );
  }

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
                Identity Verified
              </h2>
              <p className="text-muted-foreground text-sm mb-8">
                Your neural identifier has been verified. Initialize your session to access Stratum AI.
              </p>
              <Link
                to="/login"
                className="block w-full auth-gradient-btn auth-shimmer-btn text-foreground font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center transition-colors active:scale-[0.98]"
              >
                INITIALIZE SESSION
              </Link>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Error state
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
              Verification Failed
            </h2>
            <p className="text-muted-foreground text-sm mb-8">
              {error || 'The verification link is invalid or has expired.'}
            </p>
            <div className="space-y-4">
              <Link
                to="/signup"
                className="block w-full auth-gradient-btn auth-shimmer-btn text-foreground font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center transition-colors active:scale-[0.98]"
              >
                REGISTER NEW ENTITY
              </Link>
              {!showResendForm ? (
                <button
                  onClick={() => setShowResendForm(true)}
                  className="text-xs text-primary hover:text-foreground transition-colors font-bold uppercase tracking-widest"
                >
                  Resend verification
                </button>
              ) : (
                <div className="space-y-3 auth-fade-up-d1">
                  <input
                    type="email"
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    placeholder="Enter your neural identifier"
                    className="w-full h-11 bg-background/80 border dark:border-white/10 border-border/50 rounded-[12px] px-4 text-foreground text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary "
                  />
                  <button
                    onClick={async () => {
                      if (!resendEmail) return;
                      resendMutation.mutate(
                        { email: resendEmail },
                        { onSuccess: () => setShowResendForm(false) }
                      );
                    }}
                    disabled={resendMutation.isPending || !resendEmail}
                    className="text-xs text-primary hover:text-foreground transition-colors disabled:opacity-50 font-bold uppercase tracking-widest"
                  >
                    {resendMutation.isPending
                      ? 'Transmitting...'
                      : resendMutation.isSuccess
                        ? 'Verification transmitted!'
                        : 'Transmit verification'}
                  </button>
                  {resendMutation.isError && (
                    <p className="text-xs text-red-400">
                      {resendMutation.error?.message || 'Failed to resend verification.'}
                    </p>
                  )}
                  {resendMutation.isSuccess && (
                    <p className="text-xs text-emerald-400">
                      Verification transmitted. Check your inbox.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </>
  );
}


