/**
 * Login Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card form
 *
 * Fixes applied:
 * - BUG-001/002: Demo login now uses demoLogin() with client-side fallback
 * - BUG-003: Autofill captured via onInput + form ref reading on submit
 * - BUG-006: SSO button shows "Coming Soon" tooltip on hover
 * - BUG-007: Remember Me persists session via localStorage flag
 * - BUG-012: Page title no longer flickers (SEO title set immediately)
 * - BUG-016: Inline validation for email & password fields
 */

import { useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  FingerPrintIcon,
  LockClosedIcon,
  UserIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/contexts/AuthContext';
import { pageSEO, SEO } from '@/components/common/SEO';
import AuthLeftPanel from '@/components/auth/AuthLeftPanel';
import { authStyles } from '@/components/auth/authStyles';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, demoLogin } = useAuth();

  const formRef = useRef<HTMLFormElement>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingRole, setLoadingRole] = useState<string | null>(null); // BUG-019: per-button spinner
  const [error, setError] = useState('');
  const [rememberMe, setRememberMe] = useState(
    () => localStorage.getItem('stratum_remember_me') === 'true'
  );
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [ssoHover, setSsoHover] = useState(false);

  const from = location.state?.from?.pathname || '/dashboard/overview';

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
      } else {
        setError(result.error || 'Login failed');
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // BUG-001/002: Demo login now uses demoLogin() with client-side fallback
  // BUG-019: Track which demo button is loading for per-button spinner
  const handleDemoLogin = async (role: 'superadmin' | 'admin' | 'user') => {
    setError('');
    setIsLoading(true);
    setLoadingRole(role);

    try {
      const result = await demoLogin(role);
      if (result.success) {
        navigate(from, { replace: true });
      } else {
        setError(result.error || 'Demo login failed');
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
      setLoadingRole(null);
    }
  };

  return (
    <>
      <SEO {...pageSEO.login} url="https://stratum-ai.com/login" />
      <style>{authStyles}</style>

      <div className="bg-black text-white min-h-screen flex font-sans selection:bg-[#00c7be]/30 overflow-hidden">
        {/* Background effects — matching landing page Apple Glass Dark */}
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(0, 199, 190, 0.08), transparent 60%)' }} />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(139, 92, 246, 0.06), transparent 60%)' }} />
          <div className="auth-float-3 absolute top-[30%] right-[20%] w-[400px] h-[400px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(20, 240, 198, 0.05), transparent 60%)' }} />
        </div>

        <main className="relative z-10 w-full flex min-h-screen">
          {/* Left Panel — hidden on mobile */}
          <AuthLeftPanel className="hidden lg:flex" />

          {/* Right Panel — Form */}
          <section className="lg:w-5/12 w-full flex items-center justify-center p-6 lg:p-8 bg-black/50 relative">
            {/* Decorative corners — neutral white matching landing page borders */}
            <div className="absolute top-8 right-8 w-16 h-16 border-t border-r border-white/[0.08] pointer-events-none rounded-tr-2xl hidden lg:block" />
            <div className="absolute bottom-8 left-8 w-16 h-16 border-b border-l border-white/[0.08] pointer-events-none rounded-bl-2xl hidden lg:block" />

            <div className="w-full max-w-[400px] auth-glass-card rounded-[24px] p-7 shadow-2xl relative z-20 auth-fade-up">
              {/* Header */}
              <div className="mb-8 text-center">
                <div className="w-14 h-14 bg-[#00c7be]/10 rounded-full flex items-center justify-center mx-auto mb-5 border border-[#00c7be]/20">
                  <FingerPrintIcon className="w-7 h-7 text-[#00c7be]" />
                </div>
                <h2 className="text-[24px] font-display font-bold text-white mb-2">
                  Dashboard Access
                </h2>
                <p className="text-white/40 text-[14px]">
                  Authenticate to access your Stratum dashboard
                </p>
              </div>

              {/* Mobile logo */}
              <div className="lg:hidden flex items-center justify-center gap-3 mb-6">
                <div className="w-9 h-9 bg-[#00c7be] rounded-lg flex items-center justify-center shadow-lg">
                  <span className="font-display font-bold text-white text-base">S</span>
                </div>
                <span className="font-display font-bold text-lg tracking-tight text-white">
                  STRATUM AI
                </span>
              </div>

              <form ref={formRef} onSubmit={handleSubmit} className="flex flex-col gap-3">
                {/* Error Alert */}
                {error && (
                  <div className="auth-slide-in flex items-center gap-2 p-3 rounded-xl text-[13px] bg-red-500/10 border border-red-500/20 text-red-400">
                    <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                {/* Work Identity */}
                <div className="auth-fade-up-d1">
                  <label
                    htmlFor="login-email"
                    className="block text-[12px] font-bold text-white/30 uppercase tracking-wider mb-1.5 ml-1"
                  >
                    Work Identity
                  </label>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
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
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                  </div>
                  {emailError && (
                    <p id="login-email-error" className="text-xs text-red-400 mt-1 ml-1">{emailError}</p>
                  )}
                </div>

                {/* Encryption Key */}
                <div className="auth-fade-up-d2">
                  <div className="flex justify-between items-center mb-1.5 ml-1">
                    <label
                      htmlFor="login-password"
                      className="block text-[12px] font-bold text-white/30 uppercase tracking-wider"
                    >
                      Encryption Key
                    </label>
                    <Link
                      to="/forgot-password"
                      className="text-[11px] font-bold text-[#00c7be] hover:text-white transition-colors"
                    >
                      Recovery
                    </Link>
                  </div>
                  <div className="relative auth-input-glow rounded-xl transition-shadow">
                    <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
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
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-11 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
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
                <div className="flex items-center gap-2.5 py-1 auth-fade-up-d2">
                  <input
                    type="checkbox"
                    id="remember"
                    checked={rememberMe}
                    onChange={() => setRememberMe(!rememberMe)}
                    className="w-4 h-4 rounded border-white/10 bg-white/5 text-[#00c7be] focus:ring-[#00c7be] focus:ring-offset-black cursor-pointer"
                  />
                  <label
                    htmlFor="remember"
                    className="text-[12px] text-white/40 font-medium cursor-pointer select-none"
                  >
                    Maintain active session
                  </label>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="auth-fade-up-d3 w-full auth-gradient-btn auth-shimmer-btn text-white font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-3 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Signing in...
                    </span>
                  ) : (
                    <>
                      Sign in to Dashboard
                      <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                      </svg>
                    </>
                  )}
                </button>
              </form>

              {/* BUG-027: Section divider — consistent uppercase label */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-bold">
                  <span className="bg-black px-4 text-white/20">
                    Enterprise SSO
                  </span>
                </div>
              </div>

              {/* BUG-006: SSO Button — disabled with Coming Soon tooltip */}
              <div className="relative">
                <button
                  type="button"
                  disabled
                  onMouseEnter={() => setSsoHover(true)}
                  onMouseLeave={() => setSsoHover(false)}
                  className="w-full h-[44px] flex items-center justify-center bg-white/[0.04] text-[12px] font-bold text-white/30 rounded-xl border border-white/[0.06] transition-colors uppercase tracking-wider gap-2 cursor-not-allowed opacity-60"
                  aria-label="SSO authentication coming soon"
                >
                  <BuildingOfficeIcon className="w-4 h-4" />
                  Authenticate with SSO
                </button>
                {ssoHover && (
                  <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[#00c7be] text-white text-[11px] font-bold py-1 px-3 rounded-lg whitespace-nowrap z-30 shadow-lg">
                    Coming Soon
                  </div>
                )}
              </div>

              {/* BUG-027: Section divider — consistent uppercase label */}
              <div className="relative my-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-bold">
                  <span className="bg-black px-4 text-white/20">
                    Demo Access
                  </span>
                </div>
              </div>

              {/* Demo Buttons */}
              <div className="grid grid-cols-3 gap-2">
                {([
                  { role: 'superadmin' as const, label: 'Super Admin', icon: '\u26A1' },
                  { role: 'admin' as const, label: 'Admin', icon: '\uD83D\uDEE1\uFE0F' },
                  { role: 'user' as const, label: 'Viewer', icon: '\uD83D\uDC64' },
                ]).map((item) => (
                  <button
                    key={item.role}
                    type="button"
                    onClick={() => handleDemoLogin(item.role)}
                    disabled={isLoading}
                    className="group py-2.5 px-2 bg-white/[0.03] hover:bg-white/[0.06] text-[11px] font-semibold text-white/40 hover:text-white/70 rounded-xl border border-white/[0.06] hover:border-white/[0.12] transition-all disabled:opacity-50 flex flex-col items-center gap-1"
                  >
                    {/* BUG-019: Show spinner on the specific demo button that's loading */}
                    {loadingRole === item.role ? (
                      <svg className="animate-spin w-[14px] h-[14px] text-[#00c7be]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    ) : (
                      <span className="text-[14px] opacity-60 group-hover:opacity-100 transition-opacity">
                        {item.icon}
                      </span>
                    )}
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>

              {/* Bottom Link */}
              <div className="mt-6 pt-4">
                <p className="text-center text-[13px] text-white/30">
                  New entity?{' '}
                  <Link
                    to="/signup"
                    className="text-[#00c7be] font-bold hover:underline"
                  >
                    Request access
                  </Link>
                </p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
