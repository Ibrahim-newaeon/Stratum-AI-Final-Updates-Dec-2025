/**
 * Login Page - Stratum AI
 * Premium Gold/Charcoal design: Centered card with animated background
 */

import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  EnvelopeIcon,
  ExclamationCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/contexts/AuthContext';
import { pageSEO, SEO } from '@/components/common/SEO';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const pageStyles = `
  @keyframes loginFloat1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.05); }
    66% { transform: translate(-20px, 20px) scale(0.95); }
  }
  @keyframes loginFloat2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(-40px, 30px) scale(1.1); }
    66% { transform: translate(20px, -40px) scale(0.9); }
  }
  @keyframes loginFloat3 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(50px, 30px) scale(1.08); }
  }
  @keyframes loginPulseRing {
    0% { transform: scale(0.95); opacity: 0.5; }
    50% { transform: scale(1); opacity: 0.8; }
    100% { transform: scale(0.95); opacity: 0.5; }
  }
  @keyframes loginShimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  @keyframes loginFadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes loginSlideIn {
    from { opacity: 0; transform: translateX(-8px); }
    to { opacity: 1; transform: translateX(0); }
  }
  .login-float-1 { animation: loginFloat1 20s ease-in-out infinite; }
  .login-float-2 { animation: loginFloat2 25s ease-in-out infinite; }
  .login-float-3 { animation: loginFloat3 18s ease-in-out infinite; }
  .login-pulse-ring { animation: loginPulseRing 3s ease-in-out infinite; }
  .login-fade-up { animation: loginFadeUp 0.6s ease-out both; }
  .login-fade-up-d1 { animation: loginFadeUp 0.6s ease-out 0.1s both; }
  .login-fade-up-d2 { animation: loginFadeUp 0.6s ease-out 0.2s both; }
  .login-fade-up-d3 { animation: loginFadeUp 0.6s ease-out 0.3s both; }
  .login-slide-in { animation: loginSlideIn 0.4s ease-out both; }
  .login-shimmer-btn {
    background: linear-gradient(
      110deg,
      #FFD700 0%,
      #FFD700 40%,
      #FFF8DC 50%,
      #FFD700 60%,
      #FFD700 100%
    );
    background-size: 200% 100%;
  }
  .login-shimmer-btn:hover {
    animation: loginShimmer 1.5s ease infinite;
  }
  .login-input-glow:focus-within {
    box-shadow: 0 0 0 1px rgba(255, 215, 0, 0.4), 0 0 12px rgba(255, 215, 0, 0.08);
  }
  .login-card-glow {
    box-shadow:
      0 0 0 1px rgba(184, 134, 11, 0.15),
      0 24px 48px -12px rgba(0, 0, 0, 0.5),
      0 0 80px -20px rgba(255, 215, 0, 0.08);
  }
  .login-gradient-text {
    background: linear-gradient(135deg, #FFD700 0%, #B8860B 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
`;

// ---------------------------------------------------------------------------
// Stats shown below the card
// ---------------------------------------------------------------------------
const stats = [
  { label: 'Revenue Recovered', value: '$142M+' },
  { label: 'Active Brands', value: '150+' },
  { label: 'Avg ROAS Lift', value: '+22%' },
  { label: 'Uptime', value: '99.9%' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
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
    } catch (err) {
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
    } catch (err) {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <SEO {...pageSEO.login} url="https://stratum-ai.com/login" />
      <style>{pageStyles}</style>

      <div className="bg-[#0D0D12] text-[#F5F5F0] min-h-screen flex flex-col items-center justify-center relative overflow-hidden font-sans selection:bg-[#FFD700]/30">
        {/* ── Animated Background ── */}
        {/* Floating gradient orbs */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="login-float-1 absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-gradient-to-br from-[#FFD700]/[0.07] to-transparent blur-[100px]" />
          <div className="login-float-2 absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full bg-gradient-to-tl from-[#8B0000]/[0.08] to-transparent blur-[100px]" />
          <div className="login-float-3 absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-gradient-to-b from-[#B8860B]/[0.05] to-transparent blur-[80px]" />
        </div>

        {/* Subtle dot grid */}
        <div
          className="fixed inset-0 pointer-events-none opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle at 1px 1px, rgba(184, 134, 11, 0.06) 1px, transparent 0)',
            backgroundSize: '32px 32px',
          }}
        />

        {/* ── Top Navigation Bar ── */}
        <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-[24px] lg:px-[48px] py-[18px]">
          <Link to="/" className="flex items-center gap-[10px] group">
            <div className="w-[34px] h-[34px] bg-[#FFD700] rounded-[8px] flex items-center justify-center rotate-45 shadow-[0_0_20px_rgba(255,215,0,0.25)] group-hover:shadow-[0_0_30px_rgba(255,215,0,0.4)] transition-shadow">
              <span className="font-display font-bold text-[#0D0D12] text-[15px] -rotate-45">S</span>
            </div>
            <div className="hidden sm:block">
              <p className="font-display font-bold text-[14px] leading-tight tracking-tight text-white/90">STRATUM AI</p>
              <p className="text-[9px] tracking-[0.25em] text-[#FFD700]/70 font-bold uppercase">Revenue OS</p>
            </div>
          </Link>

          <div className="flex items-center gap-[16px]">
            <div className="hidden sm:flex items-center gap-[6px] px-[10px] py-[5px] rounded-full border border-[#22C55E]/30 bg-[#22C55E]/5">
              <span className="relative flex h-[6px] w-[6px]">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#22C55E] opacity-60" />
                <span className="relative inline-flex rounded-full h-[6px] w-[6px] bg-[#22C55E]" />
              </span>
              <span className="text-[10px] font-semibold text-[#22C55E]/80 uppercase tracking-wider">All Systems Operational</span>
            </div>
            <Link
              to="/signup"
              className="text-[13px] font-semibold text-white/50 hover:text-white/90 transition-colors"
            >
              Create account
            </Link>
          </div>
        </nav>

        {/* ── Main Content ── */}
        <main className="relative z-10 w-full max-w-[420px] mx-auto px-[20px] py-[100px]">
          {/* Card */}
          <div className="login-card-glow login-fade-up bg-[#16161E]/80 backdrop-blur-xl rounded-[20px] p-[28px] lg:p-[36px] border border-white/[0.06]">
            {/* Header */}
            <div className="text-center mb-[28px]">
              <div className="inline-flex items-center gap-[8px] px-[12px] py-[5px] rounded-full bg-[#FFD700]/[0.08] border border-[#FFD700]/[0.15] mb-[16px]">
                <svg className="w-[14px] h-[14px] text-[#FFD700]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
                <span className="text-[10px] font-bold text-[#FFD700] uppercase tracking-wider">Enterprise-grade Security</span>
              </div>
              <h2 className="text-[24px] lg:text-[28px] font-display font-bold mb-[6px] text-white">
                Welcome back
              </h2>
              <p className="text-[13px] text-white/40 leading-relaxed">
                Sign in to your Stratum AI dashboard
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-[16px]">
              {/* Error Alert */}
              {error && (
                <div className="login-slide-in flex items-center gap-[10px] p-[12px] rounded-[12px] text-[13px] bg-[#DC143C]/[0.08] border border-[#DC143C]/20 text-[#FF6B6B]">
                  <ExclamationCircleIcon className="w-[18px] h-[18px] flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Email Field */}
              <div className="login-fade-up-d1">
                <label
                  htmlFor="login-email"
                  className="block text-[11px] font-semibold text-white/40 uppercase tracking-[0.12em] mb-[8px]"
                >
                  Email address
                </label>
                <div className="relative login-input-glow rounded-[12px] transition-shadow">
                  <EnvelopeIcon className="absolute left-[14px] top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    disabled={isLoading}
                    className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-[#FFD700]/40 focus:bg-white/[0.06] rounded-[12px] pl-[42px] pr-[14px] py-[12px] text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="login-fade-up-d2">
                <div className="flex justify-between items-center mb-[8px]">
                  <label
                    htmlFor="login-password"
                    className="block text-[11px] font-semibold text-white/40 uppercase tracking-[0.12em]"
                  >
                    Password
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-[11px] font-semibold text-[#FFD700]/60 hover:text-[#FFD700] transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative login-input-glow rounded-[12px] transition-shadow">
                  <LockClosedIcon className="absolute left-[14px] top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-white/25 pointer-events-none" />
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    disabled={isLoading}
                    className="w-full bg-white/[0.04] border border-white/[0.08] focus:border-[#FFD700]/40 focus:bg-white/[0.06] rounded-[12px] pl-[42px] pr-[44px] py-[12px] text-[14px] transition-all outline-none text-white placeholder:text-white/20"
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    className="absolute right-[14px] top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60 transition-colors"
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
              <div className="flex items-center gap-[10px] login-fade-up-d2">
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={rememberMe}
                  onClick={() => setRememberMe(!rememberMe)}
                  className={`w-[18px] h-[18px] rounded-[5px] border flex items-center justify-center transition-all flex-shrink-0 ${
                    rememberMe
                      ? 'bg-[#FFD700] border-[#FFD700]'
                      : 'bg-white/[0.04] border-white/[0.12] hover:border-white/20'
                  }`}
                >
                  {rememberMe && (
                    <svg className="w-[12px] h-[12px] text-[#0D0D12]" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  )}
                </button>
                <span className="text-[12px] text-white/40 select-none cursor-pointer" onClick={() => setRememberMe(!rememberMe)}>
                  Keep me signed in for 30 days
                </span>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="login-fade-up-d3 w-full login-shimmer-btn text-[#0D0D12] font-bold py-[13px] rounded-[12px] shadow-[0_0_24px_rgba(255,215,0,0.25)] hover:shadow-[0_0_36px_rgba(255,215,0,0.35)] hover:scale-[1.015] active:scale-[0.985] transition-all flex items-center justify-center gap-[8px] text-[14px] disabled:opacity-50 disabled:hover:scale-100 disabled:hover:shadow-[0_0_24px_rgba(255,215,0,0.25)]"
              >
                {isLoading ? (
                  <span className="flex items-center gap-[8px]">
                    <svg className="animate-spin w-[18px] h-[18px]" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  <>
                    Sign in
                    <svg className="w-[16px] h-[16px]" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-[22px]">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/[0.06]" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-[12px] text-[10px] font-semibold text-white/25 uppercase tracking-[0.15em] bg-[#16161E]">
                  Quick Demo Access
                </span>
              </div>
            </div>

            {/* Demo Buttons */}
            <div className="grid grid-cols-3 gap-[8px]">
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
                  className="group py-[10px] px-[8px] bg-white/[0.03] hover:bg-white/[0.06] text-[11px] font-semibold text-white/40 hover:text-white/70 rounded-[10px] border border-white/[0.06] hover:border-white/[0.12] transition-all disabled:opacity-50 flex flex-col items-center gap-[4px]"
                >
                  <span className="text-[14px] opacity-60 group-hover:opacity-100 transition-opacity">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              ))}
            </div>

            {/* Sign up link */}
            <p className="text-center text-[13px] text-white/35 mt-[22px]">
              Don't have an account?{' '}
              <Link to="/signup" className="login-gradient-text font-bold hover:opacity-80 transition-opacity">
                Create one free
              </Link>
            </p>
          </div>

          {/* ── Stats Row ── */}
          <div className="login-fade-up-d3 grid grid-cols-4 gap-[8px] mt-[24px] px-[4px]">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-[16px] lg:text-[18px] font-display font-bold text-white/80">{stat.value}</p>
                <p className="text-[9px] text-white/25 uppercase tracking-wider font-medium mt-[2px]">{stat.label}</p>
              </div>
            ))}
          </div>
        </main>

        {/* ── Footer ── */}
        <footer className="fixed bottom-0 left-0 right-0 z-20 flex items-center justify-between px-[24px] lg:px-[48px] py-[16px]">
          <span className="text-[11px] text-white/20 font-medium">&copy; 2026 Stratum AI Inc.</span>
          <div className="flex gap-[20px]">
            {['Privacy', 'Terms', 'Security'].map((link) => (
              <a
                key={link}
                href="#"
                className="text-[11px] text-white/20 hover:text-white/50 font-medium transition-colors"
              >
                {link}
              </a>
            ))}
          </div>
        </footer>

        {/* ── Decorative Ring (desktop only) ── */}
        <div className="hidden lg:block fixed pointer-events-none login-pulse-ring" style={{
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '700px',
          height: '700px',
          borderRadius: '50%',
          border: '1px solid rgba(255, 215, 0, 0.03)',
        }} />
        <div className="hidden lg:block fixed pointer-events-none" style={{
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '900px',
          height: '900px',
          borderRadius: '50%',
          border: '1px solid rgba(255, 215, 0, 0.015)',
        }} />
      </div>
    </>
  );
}
