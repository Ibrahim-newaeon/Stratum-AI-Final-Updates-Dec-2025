/**
 * CMS Login Page
 * Dedicated login portal for Content Management System admins
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DocumentTextIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  EyeSlashIcon,
  PencilSquareIcon,
  PhotoIcon,
  TagIcon,
} from '@heroicons/react/24/outline';

export default function CMSLogin() {
  const navigate = useNavigate();
  const { login, user } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already logged in as admin, redirect to CMS
  if (user && (user.role === 'superadmin' || user.role === 'admin')) {
    navigate('/cms');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await login(email, password);

      if (result.success) {
        // Check if user has CMS access (superadmin or admin)
        const userRole = (result as any).user?.role;
        if (userRole === 'superadmin' || userRole === 'admin') {
          navigate('/cms');
        } else {
          setError('Access denied. CMS requires admin privileges.');
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
        }
      } else {
        setError(result.error || 'Invalid credentials');
      }
    } catch {
      setError('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-primary flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-purple-900/50 via-surface-secondary to-cyan-900/30 p-12 flex-col justify-between relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 left-20 w-64 h-64 bg-purple-500 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-20 w-64 h-64 bg-cyan-500 rounded-full blur-3xl" />
        </div>

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
              <PencilSquareIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-white">Stratum</span>
              <span className="text-xl font-light text-purple-400 ml-1">CMS</span>
            </div>
          </div>
        </div>

        {/* Feature highlights */}
        <div className="relative z-10 space-y-8">
          <h1 className="text-4xl font-bold text-white leading-tight">
            Content Management
            <br />
            <span className="bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
              Made Simple
            </span>
          </h1>
          <p className="text-lg text-white/60 max-w-md">
            Manage your website content, blog posts, FAQs, and pricing pages from one centralized
            dashboard.
          </p>

          {/* Feature cards */}
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <DocumentTextIcon className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <div className="text-white font-medium">Blog & Content</div>
                <div className="text-sm text-white/50">Create, edit, and publish blog posts</div>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <PhotoIcon className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <div className="text-white font-medium">Landing Pages</div>
                <div className="text-sm text-white/50">Manage features, FAQ, and pricing</div>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <TagIcon className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <div className="text-white font-medium">Categories & Tags</div>
                <div className="text-sm text-white/50">Organize content with taxonomy</div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 text-sm text-white/40">
          <p>Stratum AI Content Management System</p>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
              <PencilSquareIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-white">Stratum</span>
              <span className="text-xl font-light text-purple-400 ml-1">CMS</span>
            </div>
          </div>

          {/* Form header */}
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">CMS Admin Login</h2>
            <p className="text-white/60">Sign in to manage your content</p>
          </div>

          {/* Error alert */}
          {error && (
            <Alert variant="destructive" className="mb-6 bg-red-500/10 border-red-500/30">
              <ExclamationTriangleIcon className="w-4 h-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Login form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-white/80">
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@stratum.ai"
                required
                autoComplete="email"
                className="bg-white/5 border-white/10 text-white placeholder:text-white/30 focus:border-purple-500 focus:ring-purple-500/20"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-white/80">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  className="bg-white/5 border-white/10 text-white placeholder:text-white/30 focus:border-purple-500 focus:ring-purple-500/20 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="w-5 h-5" />
                  ) : (
                    <EyeIcon className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full py-6 bg-gradient-to-r from-purple-500 to-cyan-500 hover:from-purple-600 hover:to-cyan-600 text-white font-semibold"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
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
                'Sign In to CMS'
              )}
            </Button>
          </form>

          {/* Footer links */}
          <div className="mt-8 text-center space-y-4">
            <p className="text-sm text-white/40">
              Need access?{' '}
              <a href="mailto:admin@stratum.ai" className="text-purple-400 hover:underline">
                Contact your administrator
              </a>
            </p>
            <div className="pt-4 border-t border-white/10">
              <Link to="/login" className="text-sm text-white/60 hover:text-white">
                Back to main login
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
