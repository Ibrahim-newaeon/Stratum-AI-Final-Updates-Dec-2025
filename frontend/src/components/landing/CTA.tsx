import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, SparklesIcon } from '@heroicons/react/24/outline';

// Stratum Gold Dark theme
const theme = {
  gold: '#00c7be',
  goldLight: 'rgba(0, 199, 190, 0.15)',
  orange: '#FF9F0A',
  bgBase: '#000000',
  bgCard: 'rgba(255, 255, 255, 0.03)',
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.08)',
};

export function CTA() {
  const navigate = useNavigate();

  return (
    <section
      className="py-32 relative overflow-hidden"
      style={{
        background: theme.bgBase,
        borderTop: `1px solid ${theme.border}`,
        borderBottom: `1px solid ${theme.border}`,
      }}
    >
      {/* Ambient orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div
          className="absolute top-1/2 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(0, 199, 190, 0.1), transparent 60%)' }}
        />
        <div
          className="absolute top-1/2 right-1/4 translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(139, 92, 246, 0.06), transparent 60%)' }}
        />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        {/* Badge - Centered above hero */}
        <div className="flex justify-center mb-8">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
            style={{
              background: theme.goldLight,
              border: `1px solid rgba(0, 199, 190, 0.3)`,
            }}
          >
            <SparklesIcon className="w-4 h-4" style={{ color: theme.gold }} />
            <span className="text-sm font-medium" style={{ color: theme.gold }}>14-day free trial</span>
          </div>
        </div>

        {/* Hero Message - Centered */}
        <h2 className="text-4xl md:text-5xl font-bold text-white mb-6 text-center">
          Ready to transform your{' '}
          <span style={{ color: theme.gold }}>
            revenue operations?
          </span>
        </h2>

        <p className="text-lg max-w-2xl mx-auto mb-10" style={{ color: theme.textMuted }}>
          Join marketing teams who trust Stratum AI to optimize their campaigns with confidence. No
          credit card required to start.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => navigate('/signup')}
            className="group flex items-center gap-2 px-8 py-4 rounded-lg text-white font-semibold text-base
                       transition-all duration-300 hover:scale-[1.02] hover:brightness-110 active:scale-[0.98]"
            style={{
              background: theme.gold,
              boxShadow: '0 0 40px rgba(0, 199, 190, 0.3)',
            }}
          >
            14 Day Free Trial
            <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            onClick={() => navigate('/login')}
            className="px-8 py-4 rounded-lg font-medium text-base transition-all duration-200 hover:text-white hover:bg-white/5"
            style={{ color: theme.textMuted }}
          >
            Already have an account? Sign in
          </button>
        </div>

        {/* Social proof */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-8">
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-full flex items-center justify-center"
                  style={{
                    background: theme.bgCard,
                    border: `2px solid ${theme.border}`,
                  }}
                >
                  <span className="text-xs" style={{ color: theme.textMuted }}>{i}</span>
                </div>
              ))}
            </div>
            <span className="text-sm" style={{ color: theme.textMuted }}>500+ teams trust Stratum</span>
          </div>

          <div className="h-6 w-px hidden sm:block" style={{ background: theme.border }} />

          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <svg
                key={i}
                className="w-4 h-4"
                style={{ color: theme.orange }}
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
            <span className="text-sm" style={{ color: theme.textMuted }}>4.9/5 rating</span>
          </div>
        </div>
      </div>
    </section>
  );
}
