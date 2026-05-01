import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';

export function CTA() {
  const navigate = useNavigate();

  return (
    <section className="relative py-24 lg:py-32 bg-card/30 border-y border-border overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-secondary/10 blur-3xl" />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/10 border border-secondary/20 mb-8 animate-enter">
          <Sparkles className="w-4 h-4 text-secondary" />
          <span className="text-meta text-secondary">14-day free trial</span>
        </div>

        <h2
          className="text-display-sm md:text-display text-text-primary mb-6 animate-enter"
          style={{ animationDelay: '0.1s' }}
        >
          Ready to partner with <span className="text-gradient-primary">AI?</span>
        </h2>

        <p
          className="text-body text-text-secondary max-w-2xl mx-auto mb-10 animate-enter"
          style={{ animationDelay: '0.2s' }}
        >
          Join enterprise growth teams who partner with Stratum AI to optimize
          their campaigns with confidence. No credit card required to start.
        </p>

        <div
          className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-enter"
          style={{ animationDelay: '0.3s' }}
        >
          <button
            onClick={() => navigate('/signup')}
            className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold text-body shadow-glow hover:shadow-glow-orange hover:scale-[1.02] active:scale-[0.98] transition-transform transition-shadow duration-200"
          >
            Start Free — No Credit Card
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
          </button>
        </div>

        {/* Social proof */}
        <div
          className="mt-16 flex flex-wrap items-center justify-center gap-8 animate-enter"
          style={{ animationDelay: '0.4s' }}
        >
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-full bg-card border-2 border-background flex items-center justify-center"
                >
                  <span className="text-micro text-text-muted">{i}</span>
                </div>
              ))}
            </div>
            <span className="text-meta text-text-muted">
              500+ teams partner with Stratum
            </span>
          </div>

          <div className="h-6 w-px bg-border hidden sm:block" />

          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <svg
                key={i}
                className="w-4 h-4 text-secondary"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
            <span className="text-meta text-text-muted">4.9/5 rating</span>
          </div>
        </div>
      </div>
    </section>
  );
}
