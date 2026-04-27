/**
 * Login Page - Stratum AI
 * Command Center design system — split-screen layout
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, Clock, AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

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

  // Inline validation helpers
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

    // Read directly from form inputs to capture browser autofill
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
        // Persist remember-me preference
        if (rememberMe) {
          localStorage.setItem('stratum_remember_me', 'true');
        } else {
          localStorage.removeItem('stratum_remember_me');
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

      <div className="min-h-screen flex bg-[#080C14] text-[#F0EDE5] font-[Satoshi,system-ui]">
        <AuthLeftPanel />

        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative">
          {/* Mobile logo */}
          <div className="lg:hidden mb-8">
            <img
              src="/images/stratum-logo.png"
              alt="Stratum AI"
              className="h-8"
              
              loading="lazy"
              decoding="async"
            />
          </div>

          <div className="w-full max-w-md bg-[#0F1320] border border-[#1E2740] rounded-xl p-8 shadow-xl">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-2xl font-semibold text-[#F0EDE5] mb-2">
                Welcome back, partner.
              </h1>
              <p className="text-sm text-[#8B92A8]">
                Enter your credentials to access your command center.
              </p>
            </div>

            <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
              {/* Verification Banner — shown after signup redirect */}
              {showVerificationBanner && (
                <div className="flex items-start gap-2 p-3 rounded-lg text-sm bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <Mail className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <span>Please verify your email before signing in. Check your inbox for a verification link.</span>
                    <Link to="/verify-email" className="block mt-1 text-[#FF8C00] font-medium hover:text-[#FFB347] transition-colors duration-200 text-xs">
                      Resend verification email
                    </Link>
                  </div>
                </div>
              )}

              {/* Lockout Alert — shows countdown timer */}
              {isLockedOut && (
                <div className="flex items-center gap-3 p-4 rounded-lg text-sm bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <Clock className="w-5 h-5 flex-shrink-0 animate-pulse" />
                  <div className="flex-1">
                    <p className="font-semibold text-amber-300 text-sm mb-0.5">Account temporarily locked</p>
                    <p className="text-amber-400/80">
                      Too many failed attempts. Try again in{' '}
                      <span className="font-semibold text-amber-300">{formatCountdown(lockoutSeconds)}</span>
                    </p>
                  </div>
                </div>
              )}

              {/* Error Alert */}
              {error && !isLockedOut && (
                <div className="flex items-center gap-2 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="login-email" className="text-xs font-medium text-[#8B92A8] ml-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
                  <input
                    id="login-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
                    onBlur={() => setTouched((t) => ({ ...t, email: true }))}
                    placeholder="you@company.com"
                    required
                    disabled={isLoading}
                    aria-invalid={!!emailError}
                    aria-describedby={emailError ? 'login-email-error' : undefined}
                    className="w-full bg-[#181F33] border border-[#1E2740] rounded-lg pl-11 pr-4 py-3 text-sm text-[#F0EDE5] placeholder-[#5A6278] outline-none focus:ring-2 focus:ring-[#FF8C00]/30 focus:border-[#FF8C00]/50 transition-colors duration-200"
                  />
                </div>
                {emailError && (
                  <p id="login-email-error" className="text-xs text-red-400 mt-1 ml-1">{emailError}</p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <div className="flex justify-between items-center ml-1">
                  <label htmlFor="login-password" className="text-xs font-medium text-[#8B92A8]">
                    Password
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-xs text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 font-medium"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-[#5A6278] pointer-events-none" />
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
                {passwordError && (
                  <p id="login-password-error" className="text-xs text-red-400 mt-1 ml-1">{passwordError}</p>
                )}
              </div>

              {/* Remember Me */}
              <div className="flex items-center gap-3 px-1 py-1">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={() => setRememberMe(!rememberMe)}
                  className="w-4 h-4 rounded border-[#1E2740] bg-[#181F33] text-[#FF8C00] focus:ring-[#FF8C00]/30 focus:ring-offset-0 cursor-pointer"
                />
                <label htmlFor="remember" className="text-xs text-[#8B92A8] font-medium cursor-pointer select-none">
                  Keep session active for 24h
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || isLockedOut}
                className="w-full bg-gradient-to-r from-[#FF1F6D] to-[#FF8C00] text-[#080C14] font-semibold rounded-lg py-3 hover:brightness-110 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLockedOut ? (
                  <span className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Locked — {formatCountdown(lockoutSeconds)}
                  </span>
                ) : isLoading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>
          </div>

          {/* Footer links */}
          <div className="w-full max-w-md mt-8 text-center">
            <p className="text-sm text-[#5A6278]">
              Don't have an account?{' '}
              <Link
                to="/signup"
                className="text-[#FF8C00] hover:text-[#FFB347] transition-colors duration-200 font-medium"
              >
                Sign up
              </Link>
            </p>
            <div className="mt-6 flex items-center justify-center gap-6 text-xs text-[#5A6278]">
              <a href="/privacy" className="hover:text-[#8B92A8] transition-colors duration-200">Privacy</a>
              <a href="/terms" className="hover:text-[#8B92A8] transition-colors duration-200">Terms</a>
              <a href="/contact" className="hover:text-[#8B92A8] transition-colors duration-200">Support</a>
            </div>
            <p className="mt-6 text-[10px] text-[#5A6278] tracking-wider">&copy; 2026 STRATUM AI</p>
          </div>
        </section>
      </div>
    </>
  );
}

