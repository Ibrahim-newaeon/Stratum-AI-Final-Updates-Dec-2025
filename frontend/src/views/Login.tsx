/**
 * Login Page - Stratum AI
 * Gold/Crimson/Charcoal design: Two-panel layout with Revenue Lift chart + modern login form
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
// Chart data for Revenue Lift Dashboard
// ---------------------------------------------------------------------------
const chartData = [
  { day: 'Mon', value: 12400, height: '40%' },
  { day: 'Tue', value: 15200, height: '55%' },
  { day: 'Wed', value: 18900, height: '85%', highlight: true },
  { day: 'Thu', value: 14100, height: '45%' },
  { day: 'Fri', value: 22500, height: '75%' },
  { day: 'Sat', value: 28400, height: '95%' },
  { day: 'Sun', value: 21200, height: '65%' },
];

// ---------------------------------------------------------------------------
// Styles — Gold / Crimson / Charcoal
// ---------------------------------------------------------------------------
const pageStyles = `
  .login-mesh-bg {
    background-image: radial-gradient(circle at 1px 1px, rgba(184, 134, 11, 0.08) 1px, transparent 0);
    background-size: 40px 40px;
  }
  .login-hero-gradient {
    background: radial-gradient(circle at 50% -20%, rgba(139, 0, 0, 0.25) 0%, rgba(184, 134, 11, 0.1) 50%, transparent 100%), #1A1A1A;
  }
  .login-glass {
    background: rgba(20, 20, 20, 0.75);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(184, 134, 11, 0.25);
  }
  .login-glow-gold {
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
  }
  .login-glow-gold:hover {
    box-shadow: 0 0 30px rgba(255, 215, 0, 0.45);
  }
  .login-chart-bar {
    transition: all 0.3s ease-out;
  }
  .login-chart-bar:hover {
    opacity: 1;
    filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.6));
  }
  @keyframes loginSlide {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
  }
  .login-animate-slide {
    animation: loginSlide 30s linear infinite;
  }
  .login-gradient-text {
    background: linear-gradient(135deg, #FFD700 0%, #DC143C 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
`;

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

      <div className="bg-[#1A1A1A] text-[#F5F5F0] min-h-screen flex font-sans selection:bg-[#FFD700]/30 overflow-x-hidden">
        {/* Mesh dot grid background */}
        <div className="fixed inset-0 login-mesh-bg pointer-events-none opacity-40" />
        {/* Ambient glow orbs */}
        <div className="fixed top-0 right-0 w-[800px] h-[800px] bg-[#8B0000]/5 rounded-full blur-[150px] pointer-events-none" />
        <div className="fixed bottom-0 left-0 w-[800px] h-[800px] bg-[#B8860B]/5 rounded-full blur-[150px] pointer-events-none" />

        <main className="relative z-10 w-full flex flex-col lg:flex-row min-h-screen">
          {/* ================================================================
              LEFT PANEL - BRANDING + REVENUE LIFT DASHBOARD
              ================================================================ */}
          <section className="lg:w-7/12 p-8 lg:p-16 hidden lg:flex flex-col justify-between space-y-12 login-hero-gradient">
            {/* Top: Logo + Status bar */}
            <div className="space-y-8">
              <div className="flex items-center space-x-3">
                <Link to="/" className="flex items-center space-x-3 group">
                  <div className="w-10 h-10 bg-[#FFD700] rounded-lg flex items-center justify-center rotate-45 shadow-[0_0_15px_rgba(255,215,0,0.3)]">
                    <span className="font-display font-bold text-[#1A1A1A] text-xl -rotate-45">S</span>
                  </div>
                  <div>
                    <h1 className="font-display font-bold text-lg leading-tight tracking-tight">STRATUM AI</h1>
                    <p className="text-[10px] tracking-widest text-[#FFD700] font-bold uppercase">
                      Revenue OS
                    </p>
                  </div>
                </Link>
              </div>

              {/* Platform status + scrolling ticker */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-1.5 login-glass rounded-full text-[11px] font-bold uppercase tracking-wider shrink-0">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#FFD700] opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#FFD700]" />
                  </span>
                  Platform Status:{' '}
                  <span className="text-[#FFD700] ml-1">Operational</span>
                </div>
                <div className="flex-1 overflow-hidden">
                  <div className="flex gap-8 whitespace-nowrap login-animate-slide text-xs text-[#F5F5F0]/50 font-medium">
                    {[
                      'New Meta API Integration Live',
                      'Predictive LTV v2.4 Released',
                      'Dashboard latency reduced by 40%',
                      'New Meta API Integration Live',
                      'Predictive LTV v2.4 Released',
                      'Dashboard latency reduced by 40%',
                    ].map((text, i) => (
                      <span key={i} className="flex items-center gap-2">
                        <span className="text-[#FFD700]">#</span> {text}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Hero heading */}
            <div className="max-w-xl">
              <h2 className="text-4xl lg:text-6xl font-display font-extrabold leading-tight mb-6">
                Master your{' '}
                <span className="login-gradient-text italic">Revenue Lift</span>{' '}
                with real-time AI
              </h2>
              <p className="text-[#F5F5F0]/50 text-lg leading-relaxed mb-10">
                Log in to access your autonomous growth dashboard and optimize customer acquisition
                costs with Stratum's Trust-Gated Autopilot.
              </p>

              {/* Revenue Lift Dashboard Card */}
              <div className="login-glass p-8 rounded-3xl shadow-2xl relative group overflow-hidden">
                {/* Card header */}
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h3 className="font-display font-bold text-lg">Revenue Lift Dashboard</h3>
                    <p className="text-xs text-[#F5F5F0]/40">Live optimization performance</p>
                  </div>
                  <div className="flex gap-2">
                    <div className="w-8 h-8 rounded-lg bg-black/40 flex items-center justify-center cursor-pointer hover:bg-white/10 transition-colors">
                      <svg className="w-4 h-4 text-[#F5F5F0]/40" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                      </svg>
                    </div>
                    <div className="w-8 h-8 rounded-lg bg-[#FFD700]/20 flex items-center justify-center">
                      <svg className="w-4 h-4 text-[#FFD700]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Bar chart */}
                <div className="flex items-end justify-between h-48 gap-2 px-2">
                  {chartData.map((bar) => (
                    <div
                      key={bar.day}
                      className="group/bar relative flex-1 flex flex-col items-center justify-end h-full"
                    >
                      <div className="absolute -top-8 bg-black/60 text-[#FFD700] text-[10px] py-1 px-2 rounded opacity-0 group-hover/bar:opacity-100 transition-opacity whitespace-nowrap z-20">
                        ${(bar.value / 1000).toFixed(1)}k
                      </div>
                      <div
                        className={`w-full rounded-t-md login-chart-bar ${
                          bar.highlight
                            ? 'bg-[#FFD700]/60 group-hover/bar:bg-[#FFD700]'
                            : 'bg-white/10 group-hover/bar:bg-[#FFD700]/40'
                        }`}
                        style={{ height: bar.height }}
                      />
                      <div
                        className={`mt-2 text-[10px] uppercase font-bold ${
                          bar.highlight ? 'text-[#FFD700]' : 'text-[#F5F5F0]/40'
                        }`}
                      >
                        {bar.day}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Stats row */}
                <div className="grid grid-cols-3 gap-4 mt-8 pt-8 border-t border-[#B8860B]/20">
                  <div>
                    <p className="text-[10px] text-[#F5F5F0]/40 uppercase font-bold tracking-widest mb-1">
                      Total Recovery
                    </p>
                    <p className="text-xl font-display font-bold text-[#F5F5F0]">$142.8k</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#F5F5F0]/40 uppercase font-bold tracking-widest mb-1">
                      ROAS Lift
                    </p>
                    <p className="text-xl font-display font-bold text-[#FFD700]">+22.4%</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[#F5F5F0]/40 uppercase font-bold tracking-widest mb-1">
                      AI Efficiency
                    </p>
                    <p className="text-xl font-display font-bold text-[#F5F5F0]">94.2%</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center gap-8 text-xs text-[#F5F5F0]/40 font-medium">
              <span>&copy; 2026 Stratum AI</span>
              <div className="flex gap-4">
                <a className="hover:text-[#FFD700] transition-colors" href="#">
                  Status
                </a>
                <a className="hover:text-[#FFD700] transition-colors" href="#">
                  Security
                </a>
                <a className="hover:text-[#FFD700] transition-colors" href="#">
                  Privacy
                </a>
              </div>
            </div>
          </section>

          {/* ================================================================
              RIGHT PANEL - LOGIN FORM
              ================================================================ */}
          <section className="lg:w-5/12 p-6 lg:p-12 flex items-center justify-center bg-black/20 relative min-h-screen">
            {/* Corner decorations */}
            <div className="absolute top-10 right-10 w-24 h-24 border-t-2 border-r-2 border-[#FFD700]/20 pointer-events-none rounded-tr-3xl hidden lg:block" />
            <div className="absolute bottom-10 left-10 w-24 h-24 border-b-2 border-l-2 border-[#FFD700]/20 pointer-events-none rounded-bl-3xl hidden lg:block" />

            <div className="w-full max-w-md">
              {/* Mobile logo */}
              <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
                <div className="w-10 h-10 bg-[#FFD700] rounded-lg flex items-center justify-center rotate-45 shadow-[0_0_15px_rgba(255,215,0,0.3)]">
                  <span className="font-display font-bold text-[#1A1A1A] text-xl -rotate-45">S</span>
                </div>
                <span className="font-display font-bold text-xl tracking-tight">STRATUM AI</span>
              </div>

              {/* Form Card */}
              <div className="login-glass p-8 lg:p-10 rounded-[2.5rem] shadow-2xl relative z-20">
                <div className="text-center mb-10">
                  <h2 className="text-2xl lg:text-3xl font-display font-bold mb-3">
                    Welcome back
                  </h2>
                  <p className="text-[#F5F5F0]/50 text-sm">
                    Enter your credentials to access Stratum OS
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                  {error && (
                    <div className="flex items-center gap-3 p-4 rounded-xl text-sm bg-[#DC143C]/10 border border-[#DC143C]/30 text-[#DC143C]">
                      <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  {/* Work Email */}
                  <div>
                    <label
                      htmlFor="login-email"
                      className="block text-[10px] font-bold text-[#F5F5F0]/50 uppercase tracking-[0.2em] mb-2 ml-1"
                    >
                      Work Email
                    </label>
                    <div className="relative group">
                      <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#F5F5F0]/40 transition-colors group-focus-within:text-[#FFD700]" />
                      <input
                        id="login-email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="name@company.com"
                        required
                        disabled={isLoading}
                        className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700]/50 focus:ring-4 focus:ring-[#FFD700]/5 rounded-2xl pl-12 pr-4 py-4 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                      />
                    </div>
                  </div>

                  {/* Password */}
                  <div>
                    <div className="flex justify-between items-center mb-2 ml-1">
                      <label
                        htmlFor="login-password"
                        className="block text-[10px] font-bold text-[#F5F5F0]/50 uppercase tracking-[0.2em]"
                      >
                        Password
                      </label>
                      <Link
                        to="/forgot-password"
                        className="text-[10px] font-bold text-[#FFD700] hover:underline uppercase tracking-wider"
                      >
                        Forgot?
                      </Link>
                    </div>
                    <div className="relative group">
                      <LockClosedIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#F5F5F0]/40 transition-colors group-focus-within:text-[#FFD700]" />
                      <input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        required
                        disabled={isLoading}
                        className="w-full bg-black/40 border border-[#B8860B]/20 focus:border-[#FFD700]/50 focus:ring-4 focus:ring-[#FFD700]/5 rounded-2xl pl-12 pr-12 py-4 text-sm transition-all outline-none text-[#F5F5F0] placeholder:text-[#F5F5F0]/20"
                      />
                      <button
                        type="button"
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-[#F5F5F0]/40 hover:text-[#F5F5F0] transition-colors"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeSlashIcon className="w-5 h-5" />
                        ) : (
                          <EyeIcon className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Remember me */}
                  <div className="flex items-center gap-3 py-2">
                    <input
                      id="login-remember"
                      type="checkbox"
                      checked={rememberMe}
                      onChange={() => setRememberMe(!rememberMe)}
                      className="w-5 h-5 rounded-md border-[#B8860B]/30 bg-black/40 text-[#FFD700] focus:ring-offset-[#1A1A1A] focus:ring-[#FFD700] cursor-pointer"
                    />
                    <label
                      htmlFor="login-remember"
                      className="text-xs text-[#F5F5F0]/50 font-medium cursor-pointer select-none"
                    >
                      Remember me for 30 days
                    </label>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-[#FFD700] text-[#1A1A1A] font-bold py-4 rounded-2xl shadow-lg login-glow-gold hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-50 disabled:hover:scale-100"
                  >
                    {isLoading ? (
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
                        Sign in to dashboard
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2}
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
                          />
                        </svg>
                      </>
                    )}
                  </button>

                  {/* Quick Demo Access divider */}
                  <div className="relative my-8">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-[#B8860B]/20" />
                    </div>
                    <div className="relative flex justify-center text-[10px] uppercase tracking-widest font-bold">
                      <span className="bg-transparent px-4 text-[#F5F5F0]/30">Quick Demo Access</span>
                    </div>
                  </div>

                  {/* Demo role buttons */}
                  <div className="grid grid-cols-3 gap-3">
                    {(['superadmin', 'admin', 'user'] as const).map((role) => (
                      <button
                        key={role}
                        type="button"
                        onClick={() => handleDemoLogin(role)}
                        disabled={isLoading}
                        className="py-2 px-3 bg-black/40 hover:bg-white/10 text-[10px] font-bold text-[#F5F5F0]/50 rounded-lg border border-[#B8860B]/20 transition-colors uppercase tracking-wider disabled:opacity-50"
                      >
                        {role === 'superadmin' ? 'Super' : role === 'admin' ? 'Admin' : 'User'}
                      </button>
                    ))}
                  </div>

                  {/* Sign up link */}
                  <p className="text-center text-sm text-[#F5F5F0]/50 mt-10">
                    Don't have an account?{' '}
                    <Link to="/signup" className="text-[#FFD700] font-bold hover:underline">
                      Sign up
                    </Link>
                  </p>
                </form>

                {/* Terms footer */}
                <div className="mt-8 pt-8 border-t border-[#B8860B]/15 text-center">
                  <p className="text-[10px] text-[#F5F5F0]/30 uppercase tracking-widest leading-loose">
                    By signing in, you agree to our
                    <br />
                    <a className="underline hover:text-[#F5F5F0]/60" href="#">
                      Terms of Service
                    </a>{' '}
                    &amp;{' '}
                    <a className="underline hover:text-[#F5F5F0]/60" href="#">
                      Privacy Policy
                    </a>
                  </p>
                </div>
              </div>

              {/* Mobile footer */}
              <div className="lg:hidden flex justify-center mt-8 text-xs text-[#F5F5F0]/40 font-medium">
                <span>&copy; 2026 Stratum AI</span>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
