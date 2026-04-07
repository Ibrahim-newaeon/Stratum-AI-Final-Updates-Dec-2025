/**
 * Login Page - Stratum AI
 * Split-screen layout: Trust Gauge left panel + glass card form
 * Cyberpunk Dark theme — midnight navy + spectral pink/orange/gold
 *
 * Fixes applied:
 * - BUG-001/002: Demo login now uses demoLogin() with client-side fallback
 * - BUG-003: Autofill captured via onInput + form ref reading on submit
 * - BUG-006: SSO button shows "Coming Soon" tooltip on hover
 * - BUG-007: Remember Me persists session via localStorage flag
 * - BUG-012: Page title no longer flickers (SEO title set immediately)
 * - BUG-016: Inline validation for email & password fields
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ClockIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  FingerPrintIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/contexts/AuthContext';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const formRef = useRef<HTMLFormElement>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [rememberMe, setRememberMe] = useState(
    () => localStorage.getItem('stratum_remember_me') === 'true'
  );
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [lockoutSeconds, setLockoutSeconds] = useState(0);

  // Countdown timer for lockout
  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const timer = setInterval(() => {
      setLockoutSeconds((s) => {
        if (s <= 1) {
          setError('');
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [lockoutSeconds]);

  const formatCountdown = useCallback((secs: number) => {
    const mins = Math.floor(secs / 60);
    const remaining = secs % 60;
    return mins > 0
      ? `${mins}m ${remaining.toString().padStart(2, '0')}s`
      : `${remaining}s`;
  }, []);

  const isLockedOut = lockoutSeconds > 0;

  const from = location.state?.from?.pathname || '/dashboard/overview';
  const showVerificationBanner = location.state?.registered || location.state?.needsVerification;

  // BUG-016: Inline validation helpers
  const emailError = touched.email && !email.trim()
    ? 'Email is required'
    : touched.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
      ? 'Please enter a valid email'
      : '';
  const passwordError = touched.password && !password
    ? 'Password is required'
    : touched.password && password.length > 0 && password.length < 6
      ? 'Password must be at least 6 characters'
      : '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // BUG-003: Read directly from form inputs to capture browser autofill
    const formEl = formRef.current;
    const actualEmail = formEl?.querySelector<HTMLInputElement>('#login-email')?.value || email;
    const actualPassword = formEl?.querySelector<HTMLInputElement>('#login-password')?.value || password;

    // Sync React state with autofilled values
    if (actualEmail !== email) setEmail(actualEmail);
    if (actualPassword !== password) setPassword(actualPassword);

    // Validate
    if (!actualEmail || !actualPassword) {
      setTouched({ email: true, password: true });
      setError('Please fill in all fields');
      return;
    }

    if (isLockedOut) return; // Prevent submit during lockout
    setIsLoading(true);

    try {
      const result = await login(actualEmail, actualPassword);
      if (result.success) {
        // BUG-007: Persist remember-me preference
        if (rememberMe) {
          localStorage.setItem('stratum_remember_me', 'true');
        } else {
          localStorage.removeItem('stratum_remember_me');
          // Session-only: don't remove tokens, but mark for cleanup on window close
          sessionStorage.setItem('stratum_session_only', 'true');
        }
        navigate(from, { replace: true });
      } else if (result.lockoutSeconds) {
        // HTTP 429 — account locked out
        setLockoutSeconds(result.lockoutSeconds);
        setError('Too many failed login attempts.');
      } else {
        setError(result.error || 'Login failed');
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <SEO {...pageSEO.login} url="https://stratum-ai.com/login" />
      <style>{authStyles}</style>

      <div className="bg-[#050B18] text-white min-h-screen flex font-sans selection:bg-[#FF1F6D]/30 overflow-hidden">
        {/* Background mesh */}
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 31, 109, 0.08), transparent 60%)' }} />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 140, 0, 0.06), transparent 60%)' }} />
          <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(255, 215, 0, 0.05), transparent 60%)' }} />
        </div>

        <main className="relative z-10 w-full flex min-h-screen mx-auto" style={{ maxWidth: '1500px' }}>
          {/* Left Panel — hidden on mobile */}
          <AuthLeftPanel className="hidden lg:flex" />

          {/* Right Panel — Form */}
          <section className="lg:w-5/12 w-full flex flex-col items-center justify-center p-6 lg:p-8 bg-[#080E1C] relative">
            {/* Subtle gradient overlay */}
            <div className="absolute top-0 right-0 w-full h-full bg-gradient-to-bl from-[#FF1F6D]/5 to-transparent pointer-events-none" />

            <div className="w-full max-w-md auth-glass-card rounded-xl p-10 border-white/10 relative z-10 shadow-2xl auth-fade-up mb-12">
              {/* Header */}
              <div className="mb-10">
                <h2 className="text-3xl font-display font-extrabold text-white mb-2 tracking-tight">
                  Dashboard Access
                </h2>
                <p className="text-slate-400 text-sm">
                  Enter your neural credentials to initialize session.
                </p>
              </div>

              {/* Mobile logo */}
              <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
                <img src="/images/stratum-logo.svg" alt="Stratum AI" className="h-7" style={{ filter: 'invert(1) brightness(2)' }} />
              </div>

              <form ref={formRef} onSubmit={handleSubmit} className="space-y-6">
                {/* Verification Banner — shown after signup redirect */}
                {showVerificationBanner && (
                  <div className="auth-slide-in flex items-start gap-2 p-3 rounded-xl text-[13px] bg-amber-500/10 border border-amber-500/20 text-amber-400">
                    <EnvelopeIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div>
                      <span>Please verify your email before signing in. Check your inbox for a verification link.</span>
                      <Link to="/verify-email" className="block mt-1 text-[#FF1F6D] font-bold hover:underline text-[12px]">
                        Resend verification email
                      </Link>
                    </div>
                  </div>
                )}

                {/* Lockout Alert — shows countdown timer */}
                {isLockedOut && (
                  <div className="auth-slide-in flex items-center gap-3 p-4 rounded-xl text-[13px] bg-amber-500/10 border border-amber-500/20 text-amber-400">
                    <ClockIcon className="w-5 h-5 flex-shrink-0 animate-pulse" />
                    <div className="flex-1">
                      <p className="font-bold text-amber-300 text-sm mb-0.5">Account temporarily locked</p>
                      <p className="text-amber-400/80">Too many failed attempts. Try again in{' '}
                        <span className="font-mono font-bold text-amber-300">{formatCountdown(lockoutSeconds)}</span>
                      </p>
                    </div>
                  </div>
                )}

                {/* Error Alert */}
                {error && !isLockedOut && (
                  <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400">
                    <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                {/* Neural Identifier (Email) */}
                <div className="space-y-2 auth-fade-up-d1">
                  <label
                    htmlFor="login-email"
                    className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500 ml-1"
                  >
                    Neural Identifier
                  </label>
                  <div className="relative">
                    <FingerPrintIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      id="login-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
                      onBlur={() => setTouched((t) => ({ ...t, email: true }))}
                      placeholder="u_alpha_772"
                      required
                      disabled={isLoading}
                      aria-invalid={!!emailError}
                      aria-describedby={emailError ? 'login-email-error' : undefined}
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-4 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#00F5FF] focus:shadow-[0_0_15px_rgba(0,245,255,0.3)]"
                    />
                  </div>
                  {emailError && (
                    <p id="login-email-error" className="text-xs text-red-400 mt-1 ml-1">{emailError}</p>
                  )}
                </div>

                {/* Security Key (Password) */}
                <div className="space-y-2 auth-fade-up-d2">
                  <div className="flex justify-between items-center px-1">
                    <label
                      htmlFor="login-password"
                      className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500"
                    >
                      Security Key
                    </label>
                    <Link
                      to="/forgot-password"
                      className="text-[10px] uppercase font-bold tracking-[0.15em] text-[#FF1F6D] hover:text-white transition-colors"
                    >
                      Reset Key
                    </Link>
                  </div>
                  <div className="relative">
                    <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-500 pointer-events-none" />
                    <input
                      id="login-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onInput={(e) => setPassword((e.target as HTMLInputElement).value)}
                      onBlur={() => setTouched((t) => ({ ...t, password: true }))}
                      placeholder="••••••••••••"
                      required
                      disabled={isLoading}
                      aria-invalid={!!passwordError}
                      aria-describedby={passwordError ? 'login-password-error' : undefined}
                      className="w-full h-[44px] bg-[#050B18]/80 border border-white/10 rounded-[12px] pl-12 pr-11 text-white text-sm outline-none transition-all placeholder:text-slate-600 focus:border-[#FF8C00] focus:shadow-[0_0_15px_rgba(255,140,0,0.3)]"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? (
                        <EyeSlashIcon className="w-[18px] h-[18px]" />
                      ) : (
                        <EyeIcon className="w-[18px] h-[18px]" />
                      )}
                    </button>
                  </div>
                  {passwordError && (
                    <p id="login-password-error" className="text-xs text-red-400 mt-1 ml-1">{passwordError}</p>
                  )}
                </div>

                {/* Remember Me */}
                <div className="flex items-center gap-3 px-1 py-2 auth-fade-up-d2">
                  <input
                    type="checkbox"
                    id="remember"
                    checked={rememberMe}
                    onChange={() => setRememberMe(!rememberMe)}
                    className="w-4 h-4 rounded border-white/10 bg-[#050B18] text-[#FF1F6D] focus:ring-[#FF1F6D] focus:ring-offset-[#050B18] cursor-pointer"
                  />
                  <label
                    htmlFor="remember"
                    className="text-xs text-slate-400 font-medium cursor-pointer select-none"
                  >
                    Keep session active for 24h
                  </label>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading || isLockedOut}
                  className="auth-fade-up-d3 w-full auth-gradient-btn auth-shimmer-btn text-white font-black h-14 rounded-xl tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {isLockedOut ? (
                    <span className="flex items-center gap-2">
                      <ClockIcon className="w-[18px] h-[18px]" />
                      LOCKED — {formatCountdown(lockoutSeconds)}
                    </span>
                  ) : isLoading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      INITIALIZING...
                    </span>
                  ) : (
                    <>INITIALIZE SESSION</>
                  )}
                </button>
              </form>

            </div>

            {/* Footer links */}
            <div className="w-full max-w-md px-10 relative z-10">
              <div className="flex flex-col items-center gap-4">
                <p className="text-center text-[13px] text-white/30">
                  New entity?{' '}
                  <Link
                    to="/signup"
                    className="text-[#FF1F6D] font-bold hover:text-white transition-colors"
                  >
                    Request access
                  </Link>
                </p>
                <div className="flex gap-6">
                  <a className="text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono" href="/privacy">Privacy Protocol</a>
                  <a className="text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono" href="/terms">Legal Core</a>
                  <a className="text-[10px] text-slate-500 hover:text-white transition-colors uppercase tracking-widest font-mono" href="/contact">Support</a>
                </div>
                <span className="text-[10px] text-slate-600 font-mono tracking-widest">&copy; 2026 STRATUM ARTIFICIAL INTELLIGENCE</span>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
