/**
 * Login Page - Stratum HoloGlass Theme
 * Deep black background (#0b1215) + gold accent frosted glass cards
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

// Stratum Theme v4.0 - Trust-Gated Autopilot
const theme = {
  primary: '#00c7be', // Stratum Gold
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  primaryBright: '#f0c95c',
  green: '#34c759', // Status Success
  orange: '#f59e0b', // Status Warning
  purple: '#8b5cf6', // Accent Purple
  cyan: '#00c7be', // Accent Cyan
  bgVoid: '#050508', // Deepest background
  bgBase: '#0b1215', // Deep navy black
  bgCard: 'rgba(18, 18, 26, 0.9)', // Card background
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.06)',
  borderHover: 'rgba(255, 255, 255, 0.10)',
  borderGold: 'rgba(0, 199, 190, 0.15)',
  success: '#34c759',
  goldGlow: 'rgba(0, 199, 190, 0.5)',
  goldSubtle: 'rgba(0, 199, 190, 0.1)',
};

// HUD Corner component for sci-fi styling
const HUDCorner = ({ position }: { position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' }) => {
  const styles: Record<string, React.CSSProperties> = {
    'top-left': { top: 20, left: 20, borderRight: 'none', borderBottom: 'none' },
    'top-right': { top: 20, right: 20, borderLeft: 'none', borderBottom: 'none' },
    'bottom-left': { bottom: 20, left: 20, borderRight: 'none', borderTop: 'none' },
    'bottom-right': { bottom: 20, right: 20, borderLeft: 'none', borderTop: 'none' },
  };
  return (
    <div
      className="hidden lg:block fixed pointer-events-none"
      style={{
        width: 60,
        height: 60,
        border: `2px solid ${theme.primary}`,
        opacity: 0.4,
        zIndex: 1,
        ...styles[position],
      }}
    />
  );
};

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
      superadmin: { email: 'superadmin@stratum.ai', password: 'Admin123!' },
      admin: { email: 'demo@stratum.ai', password: 'demo1234' },
      user: { email: 'demo@stratum.ai', password: 'demo1234' },
    };

    const { email, password } = credentials[role];
    setEmail(email);
    setPassword(password);
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

  return (
    <div className="min-h-screen flex" style={{ background: theme.bgVoid }}>
      <SEO {...pageSEO.login} url="https://stratum-ai.com/login" />

      {/* HUD Corners */}
      <HUDCorner position="top-left" />
      <HUDCorner position="top-right" />
      <HUDCorner position="bottom-left" />
      <HUDCorner position="bottom-right" />

      {/* Ambient orbs background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 40% 40% at 20% 30%, ${theme.goldSubtle}, transparent),
            radial-gradient(ellipse 30% 30% at 80% 70%, rgba(139, 92, 246, 0.06), transparent),
            radial-gradient(ellipse 35% 35% at 60% 20%, rgba(0, 199, 190, 0.05), transparent)
          `,
        }}
      />

      {/* LEFT PANEL - BRANDING */}
      <div className="hidden lg:flex lg:w-1/2 relative" style={{ background: theme.bgVoid }}>
        <div className="absolute inset-y-0 right-0 w-px" style={{ background: theme.border }} />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div>
            <Link to="/" className="flex items-center gap-3 mb-16 group">
              <div
                className="h-10 w-10 rounded-2xl flex items-center justify-center transition-all duration-300 group-hover:scale-105"
                style={{ background: theme.primary }}
              >
                <span className="text-white font-semibold text-lg">S</span>
              </div>
              <div>
                <span
                  className="text-xl font-semibold tracking-tight"
                  style={{ color: theme.textPrimary }}
                >
                  Stratum AI
                </span>
                <div
                  className="text-xs tracking-widest uppercase"
                  style={{ color: theme.primary }}
                >
                  Revenue OS
                </div>
              </div>
            </Link>

            <h1
              className="text-4xl font-semibold mb-4 leading-tight"
              style={{ color: theme.textPrimary, letterSpacing: '-0.02em' }}
            >
              Revenue Operating
              <br />
              System with
              <br />
              <span style={{ color: theme.primary }}>Trust-Gated</span> Autopilot
            </h1>
            <p className="text-lg max-w-md leading-relaxed" style={{ color: theme.textMuted }}>
              AI-powered marketing intelligence with real-time attribution and automated
              optimization.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {['Meta', 'Google', 'TikTok', 'Snap'].map((platform) => (
                <div
                  key={platform}
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-medium transition-all duration-300"
                  style={{
                    background: theme.bgCard,
                    backdropFilter: 'blur(40px)',
                    color: theme.textMuted,
                    border: `1px solid ${theme.border}`,
                  }}
                >
                  {platform.slice(0, 2)}
                </div>
              ))}
            </div>
            <p className="text-sm" style={{ color: theme.textMuted }}>
              Integrated with all major ad platforms
            </p>
          </div>

          <div className="grid grid-cols-3 gap-6">
            {[
              { value: '150+', label: 'Growth Teams' },
              { value: '$12M+', label: 'Revenue Recovered' },
              { value: '4.2x', label: 'Avg ROAS Lift' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl font-semibold" style={{ color: theme.textPrimary }}>
                  {stat.value}
                </div>
                <div className="text-sm" style={{ color: theme.textMuted }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL - LOGIN FORM */}
      <div className="flex-1 flex items-center justify-center p-8 relative z-10">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <div
              className="h-10 w-10 rounded-2xl flex items-center justify-center"
              style={{ background: theme.primary }}
            >
              <span className="text-white font-semibold text-lg">S</span>
            </div>
            <span className="text-xl font-semibold" style={{ color: theme.textPrimary }}>
              Stratum AI
            </span>
          </div>

          <div
            className="p-8 rounded-3xl"
            style={{
              background: theme.bgCard,
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
              border: `1px solid ${theme.border}`,
              boxShadow: '0 25px 50px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div className="text-center mb-8">
              <h2 className="text-2xl font-semibold mb-2" style={{ color: theme.textPrimary }}>
                Welcome back
              </h2>
              <p style={{ color: theme.textMuted }}>Sign in to continue to your dashboard</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div
                  className="flex items-center gap-3 p-4 rounded-xl text-sm"
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#EF4444',
                  }}
                >
                  <ExclamationCircleIcon className="w-5 h-5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  Work Email
                </label>
                <div className="relative">
                  <EnvelopeIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                    placeholder="name@company.com"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                    Password
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-sm transition-colors hover:underline"
                    style={{ color: theme.primary }}
                  >
                    Forgot?
                  </Link>
                </div>
                <div className="relative">
                  <LockClosedIcon
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: theme.textMuted }}
                  />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-12 pr-12 py-3 rounded-2xl outline-none transition-all duration-200"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textPrimary,
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = theme.primary;
                      e.target.style.boxShadow = `0 0 0 3px ${theme.primaryLight}`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = theme.border;
                      e.target.style.boxShadow = 'none';
                    }}
                    placeholder="Enter your password"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                    style={{ color: theme.textMuted }}
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

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setRememberMe(!rememberMe)}
                  className="w-5 h-5 rounded-md flex items-center justify-center transition-all duration-200"
                  style={{
                    background: rememberMe ? theme.primary : theme.bgCard,
                    border: rememberMe ? 'none' : `1px solid ${theme.border}`,
                  }}
                >
                  {rememberMe && (
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </button>
                <span className="text-sm" style={{ color: theme.textMuted }}>
                  Remember me for 30 days
                </span>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 rounded-2xl font-semibold text-black transition-all duration-200 disabled:opacity-50"
                style={{
                  background: theme.primary,
                  boxShadow: '0 0 30px rgba(0, 199, 190, 0.2)',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 0 40px rgba(0, 199, 190, 0.3)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 199, 190, 0.2)';
                }}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
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
                  'Sign in'
                )}
              </button>
            </form>

            <div className="mt-6 pt-6" style={{ borderTop: `1px solid ${theme.border}` }}>
              <p className="text-center text-xs mb-3" style={{ color: theme.textMuted }}>
                Quick Demo Access
              </p>
              <div className="grid grid-cols-3 gap-2">
                {['superadmin', 'admin', 'user'].map((role) => (
                  <button
                    key={role}
                    onClick={() => handleDemoLogin(role as any)}
                    disabled={isLoading}
                    className="px-3 py-2 rounded-xl text-xs font-medium capitalize transition-all duration-200 disabled:opacity-50"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                      color: theme.textMuted,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = theme.borderHover;
                      e.currentTarget.style.color = theme.primary;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = theme.border;
                      e.currentTarget.style.color = theme.textMuted;
                    }}
                  >
                    {role === 'superadmin' ? 'Super' : role}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-center text-sm mt-6" style={{ color: theme.textMuted }}>
              Don't have an account?{' '}
              <Link
                to="/signup"
                className="font-medium transition-colors hover:underline"
                style={{ color: theme.primary }}
              >
                Sign up
              </Link>
            </p>
          </div>

          <p className="text-center text-xs mt-6" style={{ color: theme.textMuted }}>
            By signing in, you agree to our{' '}
            <a href="#" className="hover:underline" style={{ color: theme.textSecondary }}>
              Terms
            </a>{' '}
            and{' '}
            <a href="#" className="hover:underline" style={{ color: theme.textSecondary }}>
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
