import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, SparklesIcon } from '@heroicons/react/24/outline';

export function CTA() {
  const navigate = useNavigate();

  return (
    <section className="py-32 border-y border-gray-200 relative overflow-hidden" style={{ background: '#FFFFFF' }}>
      {/* Subtle background effects */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-indigo-100/40 via-indigo-50/20 to-indigo-100/40 blur-3xl opacity-50" />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-200 mb-8">
          <SparklesIcon className="w-4 h-4 text-indigo-600" />
          <span className="text-meta text-indigo-600">14-day free trial</span>
        </div>

        <h2 className="text-h1 md:text-[40px] text-black mb-6">
          Ready to transform your{' '}
          <span className="bg-gradient-to-r from-indigo-700 to-indigo-500 bg-clip-text text-transparent">
            ad operations?
          </span>
        </h2>

        <p className="text-body text-gray-500 max-w-2xl mx-auto mb-10">
          Join marketing teams who trust Stratum AI to optimize their campaigns
          with confidence. No credit card required to start.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => navigate('/signup')}
            className="group flex items-center gap-2 px-8 py-4 rounded-lg text-white font-semibold text-body
                       transition-all duration-base hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
              boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)',
            }}
          >
            14 Day Free Trial
            <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            onClick={() => navigate('/login')}
            className="px-8 py-4 rounded-lg text-gray-500 hover:text-black font-medium text-body transition-colors"
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
                  className="w-8 h-8 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center"
                >
                  <span className="text-micro text-gray-500">{i}</span>
                </div>
              ))}
            </div>
            <span className="text-meta text-gray-500">500+ teams trust Stratum</span>
          </div>

          <div className="h-6 w-px bg-gray-200 hidden sm:block" />

          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <svg
                key={i}
                className="w-4 h-4 text-amber-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
            <span className="text-meta text-gray-500">4.9/5 rating</span>
          </div>
        </div>
      </div>
    </section>
  );
}
