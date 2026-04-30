/**
 * Login Page — Stratum figma theme
 * Split-screen: testimonial panel + ember-accented sign-in form
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, Clock, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';

const FONT_STACK = 'Geist, system-ui, sans-serif';
const MONO_STACK = 'Geist Mono, monospace';

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
    return mins > 0 ? `${mins}m ${remaining.toString().padStart(2, '0')}s` : `${remaining}s`;
  }, []);

  const isLockedOut = lockoutSeconds > 0;

  const from = location.state?.from?.pathname || '/dashboard/overview';
  const showVerificationBanner = location.state?.registered || location.state?.needsVerification;

  const emailError =
    touched.email && !email.trim()
      ? 'Email is required'
      : touched.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
        ? 'Please enter a valid email'
        : '';
  const passwordError =
    touched.password && !password
      ? 'Password is required'
      : touched.password && password.length > 0 && password.length < 6
        ? 'Password must be at least 6 characters'
        : '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const formEl = formRef.current;
    const actualEmail = formEl?.querySelector<HTMLInputElement>('#login-email')?.value || email;
    const actualPassword =
      formEl?.querySelector<HTMLInputElement>('#login-password')?.value || password;

    if (actualEmail !== email) setEmail(actualEmail);
    if (actualPassword !== password) setPassword(actualPassword);

    if (!actualEmail || !actualPassword) {
      setTouched({ email: true, password: true });
      setError('Please fill in all fields');
      return;
    }

    if (isLockedOut) return;
    setIsLoading(true);

    try {
      const result = await login(actualEmail, actualPassword);
      if (result.success) {
        if (rememberMe) {
          localStorage.setItem('stratum_remember_me', 'true');
        } else {
          localStorage.removeItem('stratum_remember_me');
          sessionStorage.setItem('stratum_session_only', 'true');
        }
        navigate(from, { replace: true });
      } else if (result.lockoutSeconds) {
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

      <div className="min-h-screen flex bg-[#0B0B0B] text-white" style={{ fontFamily: FONT_STACK }}>
        <AuthLeftPanel />

        <section className="w-full lg:w-3/5 flex flex-col items-center justify-center p-6 lg:p-12 relative overflow-hidden">
          {/* Top ember glow */}
          <div
            className="absolute inset-x-0 top-0 h-72 pointer-events-none"
            style={{
              background:
                'radial-gradient(60% 60% at 50% 0%, rgba(255,90,31,0.16) 0%, rgba(255,90,31,0.04) 40%, transparent 70%)',
            }}
            aria-hidden="true"
          />

          {/* Mobile wordmark */}
          <div className="lg:hidden mb-8 self-start">
            <a href="/landing.html" className="text-[18px] font-medium tracking-tight text-white">
              stratum.ai
            </a>
          </div>

          <div className="w-full max-w-[420px] relative z-10">
            {/* Heading */}
            <div className="mb-8">
              <span
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11.5px] uppercase tracking-[0.06em] font-medium text-[#ECECEC] mb-5"
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid #1F1F1F',
                }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full bg-[#FF5A1F]"
                  style={{ boxShadow: '0 0 8px #FF5A1F' }}
                />
                Sign in
              </span>
              <h1 className="text-[34px] leading-[1.1] tracking-tight font-medium mt-5">
                Welcome back.
              </h1>
              <p className="text-[14.5px] text-[#9A9A9A] mt-2">
                Access your trust-gated revenue operations.
              </p>
            </div>

            <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
              {/* Verification banner */}
              {showVerificationBanner && (
                <div className="flex items-start gap-2 p-3 rounded-[12px] text-sm bg-[rgba(255,90,31,0.06)] border border-[#FF5A1F]/30 text-[#FFB89A]">
                  <Mail className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <span>
                      Please verify your email before signing in. Check your inbox for a
                      verification link.
                    </span>
                    <Link
                      to="/verify-email"
                      className="block mt-1 text-[#FF5A1F] font-medium hover:text-[#FF8A4A] transition-colors text-xs"
                    >
                      Resend verification email
                    </Link>
                  </div>
                </div>
              )}

              {/* Lockout */}
              {isLockedOut && (
                <div className="flex items-center gap-3 p-4 rounded-[12px] text-sm bg-[rgba(255,90,31,0.06)] border border-[#FF5A1F]/30 text-[#FFB89A]">
                  <Clock className="w-5 h-5 flex-shrink-0 animate-pulse" />
                  <div className="flex-1">
                    <p className="font-semibold text-white text-sm mb-0.5">
                      Account temporarily locked
                    </p>
                    <p>
                      Too many failed attempts. Try again in{' '}
                      <span className="font-semibold text-white">
                        {formatCountdown(lockoutSeconds)}
                      </span>
                    </p>
                  </div>
                </div>
              )}

              {/* Error */}
              {error && !isLockedOut && (
                <div className="flex items-center gap-2 p-3 rounded-[12px] text-sm bg-red-500/10 border border-red-500/30 text-red-400">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Email */}
              <div className="space-y-2">
                <label
                  htmlFor="login-email"
                  className="text-[11px] uppercase tracking-[0.12em] text-[#6B6B6B] ml-1"
                  style={{ fontFamily: MONO_STACK }}
                >
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
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
                    className="w-full h-12 bg-[rgba(255,255,255,0.015)] border border-[#1F1F1F] rounded-[12px] pl-11 pr-4 text-sm text-white placeholder-[#6B6B6B] outline-none focus:ring-4 focus:ring-[#FF5A1F]/[0.12] focus:border-[#FF5A1F]/50 transition-colors"
                  />
                </div>
                {emailError && (
                  <p id="login-email-error" className="text-xs text-red-400 mt-1 ml-1">
                    {emailError}
                  </p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <div className="flex justify-between items-center ml-1">
                  <label
                    htmlFor="login-password"
                    className="text-[11px] uppercase tracking-[0.12em] text-[#6B6B6B]"
                    style={{ fontFamily: MONO_STACK }}
                  >
                    Password
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-xs text-[#FF5A1F] hover:text-[#FF8A4A] transition-colors font-medium"
                  >
                    Forgot?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#6B6B6B] pointer-events-none" />
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
                    className="w-full h-12 bg-[rgba(255,255,255,0.015)] border border-[#1F1F1F] rounded-[12px] pl-11 pr-11 text-sm text-white placeholder-[#6B6B6B] outline-none focus:ring-4 focus:ring-[#FF5A1F]/[0.12] focus:border-[#FF5A1F]/50 transition-colors"
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B6B6B] hover:text-white transition-colors"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {passwordError && (
                  <p id="login-password-error" className="text-xs text-red-400 mt-1 ml-1">
                    {passwordError}
                  </p>
                )}
              </div>

              {/* Remember me */}
              <label className="flex items-center gap-2.5 select-none cursor-pointer pt-1">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={() => setRememberMe(!rememberMe)}
                  className="w-4 h-4 rounded border border-[#262626] bg-[#141414] accent-[#FF5A1F] cursor-pointer"
                />
                <span className="text-[13px] text-[#9A9A9A]">Keep session active for 24h</span>
              </label>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading || isLockedOut}
                className="w-full h-12 rounded-full bg-[#FF5A1F] text-white font-medium text-[14px] flex items-center justify-center gap-2 transition-all hover:bg-[#FF6E3A] hover:-translate-y-px disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed"
                style={{ boxShadow: '0 4px 14px rgba(255,90,31,0.3)' }}
              >
                {isLockedOut ? (
                  <span className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Locked — {formatCountdown(lockoutSeconds)}
                  </span>
                ) : isLoading ? (
                  <span className="flex items-center gap-2">
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
                    Signing in...
                  </span>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Footer */}
            <div className="mt-10 pt-6 border-t border-[#1F1F1F]">
              <p className="text-[13px] text-[#9A9A9A]">
                Don't have an account?
                <Link
                  to="/signup"
                  className="text-white hover:text-[#FF5A1F] transition-colors font-medium ml-1"
                >
                  Create one
                </Link>
              </p>
              <div
                className="mt-6 flex items-center gap-5 text-[11px] uppercase tracking-[0.12em] text-[#6B6B6B]"
                style={{ fontFamily: MONO_STACK }}
              >
                <a href="/privacy" className="hover:text-white transition-colors">
                  Privacy
                </a>
                <a href="/terms" className="hover:text-white transition-colors">
                  Terms
                </a>
                <a href="/contact" className="hover:text-white transition-colors">
                  Support
                </a>
              </div>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
