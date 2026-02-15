/**
 * Login Page - Stratum AI
 * Split-screen layout: Branding left panel + glass card form
 */

import { useState } from 'react';
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
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [rememberMe, setRememberMe] = useState(false);

  const from = location.state?.from?.pathname || '/dashboard/overview';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await login(email, password);
      if (result.success) {
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

  const handleDemoLogin = async (role: 'superadmin' | 'admin' | 'user') => {
    const credentials = {
      superadmin: { email: 'ibrahim@new-aeon.com', password: 'Newaeon@2025' },
      admin: { email: 'demo@stratum.ai', password: 'demo1234' },
      user: { email: 'demo@stratum.ai', password: 'demo1234' },
    };

    const { email: demoEmail, password: demoPassword } = credentials[role];
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError('');
    setIsLoading(true);

    try {
      const result = await login(demoEmail, demoPassword);
      if (result.success) {
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

  return (
    <>
      <SEO {...pageSEO.login} url="https://stratum-ai.com/login" />
      <style>{authStyles}</style>

      <div className="bg-[#0b1215] text-white min-h-screen flex font-sans selection:bg-[#00c7be]/30 overflow-hidden">
        {/* Background effects */}
        <div className="fixed inset-0 auth-cyber-grid pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="auth-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-gradient-to-br from-[#00c7be]/[0.07] to-transparent blur-[100px]" />
          <div className="auth-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full bg-gradient-to-tl from-[#00c7be]/[0.05] to-transparent blur-[100px]" />
        </div>

        <main className="relative z-10 w-full flex min-h-screen">
          {/* Left Panel — hidden on mobile */}
          <AuthLeftPanel className="hidden lg:flex" />

          {/* Right Panel — Form */}
          <section className="lg:w-5/12 w-full flex items-center justify-center p-6 lg:p-8 bg-[#0b1215]/50 relative">
            {/* Decorative corners */}
            <div className="absolute top-8 right-8 w-16 h-16 border-t border-r border-[#00c7be]/20 pointer-events-none rounded-tr-2xl hidden lg:block" />
            <div className="absolute bottom-8 left-8 w-16 h-16 border-b border-l border-[#00c7be]/20 pointer-events-none rounded-bl-2xl hidden lg:block" />

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

              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
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
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      required
                      disabled={isLoading}
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-4 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                  </div>
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
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      disabled={isLoading}
                      className="w-full h-[44px] bg-white/[0.04] border border-white/[0.08] focus:border-[#00c7be]/50 focus:ring-4 focus:ring-[#00c7be]/5 rounded-xl pl-11 pr-11 text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                    />
                    <button
                      type="button"
                      tabIndex={-1}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeSlashIcon className="w-[18px] h-[18px]" />
                      ) : (
                        <EyeIcon className="w-[18px] h-[18px]" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Remember Me */}
                <div className="flex items-center gap-2.5 py-1 auth-fade-up-d2">
                  <input
                    type="checkbox"
                    id="remember"
                    checked={rememberMe}
                    onChange={() => setRememberMe(!rememberMe)}
                    className="w-4 h-4 rounded border-white/10 bg-white/5 text-[#00c7be] focus:ring-[#00c7be] focus:ring-offset-[#0b1215] cursor-pointer"
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
                  className="auth-fade-up-d3 w-full auth-gradient-btn auth-shimmer-btn text-[#0b1215] font-bold h-[46px] rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-3 text-[14px] disabled:opacity-50 disabled:hover:scale-100"
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

              {/* Enterprise Protocol Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-bold">
                  <span className="bg-[#0d1419] px-4 text-white/20">
                    Enterprise Protocol
                  </span>
                </div>
              </div>

              {/* SSO Button */}
              <button
                type="button"
                className="w-full h-[44px] flex items-center justify-center bg-white/[0.04] hover:bg-white/[0.08] text-[12px] font-bold text-white/50 rounded-xl border border-white/[0.08] transition-colors uppercase tracking-wider gap-2"
              >
                <BuildingOfficeIcon className="w-4 h-4" />
                Authenticate with SSO
              </button>

              {/* Quick Demo Access Divider */}
              <div className="relative my-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-bold">
                  <span className="bg-[#0d1419] px-4 text-white/20">
                    Quick Demo Access
                  </span>
                </div>
              </div>

              {/* Demo Buttons */}
              <div className="grid grid-cols-3 gap-2">
                {([
                  { role: 'superadmin' as const, label: 'Super Admin', icon: '⚡' },
                  { role: 'admin' as const, label: 'Admin', icon: '🛡️' },
                  { role: 'user' as const, label: 'Viewer', icon: '👤' },
                ]).map((item) => (
                  <button
                    key={item.role}
                    type="button"
                    onClick={() => handleDemoLogin(item.role)}
                    disabled={isLoading}
                    className="group py-2.5 px-2 bg-white/[0.03] hover:bg-white/[0.06] text-[11px] font-semibold text-white/40 hover:text-white/70 rounded-xl border border-white/[0.06] hover:border-white/[0.12] transition-all disabled:opacity-50 flex flex-col items-center gap-1"
                  >
                    <span className="text-[14px] opacity-60 group-hover:opacity-100 transition-opacity">
                      {item.icon}
                    </span>
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
