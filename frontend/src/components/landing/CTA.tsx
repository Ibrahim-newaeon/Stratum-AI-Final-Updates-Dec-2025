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
          className="text-display-sm md:text-display text-foreground mb-6 animate-enter"
          style={{ animationDelay: '0.1s' }}
        >
          Ready to partner with <span className="text-gradient-primary">AI?</span>
        </h2>

        <p
          className="text-body text-muted-foreground max-w-2xl mx-auto mb-10 animate-enter"
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

        {/* Capability strip.
         *
         * This was a social-proof block: five placeholder avatars beside
         * "500+ teams partner with Stratum", and five filled stars beside
         * "4.9/5 rating". Neither was real. A fabricated aggregate rating is a
         * regulated claim, not a design detail, and this component renders on
         * the blog and marketing pages.
         *
         * Replaced with statements that are true and checkable: the platforms
         * the product integrates with, and what the trust gate does.
         */}
        <div
          className="mt-16 flex flex-wrap items-center justify-center gap-8 animate-enter"
          style={{ animationDelay: '0.4s' }}
        >
          <span className="text-meta text-muted-foreground">
            Meta · Google Ads · TikTok · Snapchat
          </span>

          <div className="h-6 w-px bg-border hidden sm:block" />

          <span className="text-meta text-muted-foreground">
            Every automated action gated, logged, and reversible
          </span>
        </div>
      </div>
    </section>
  );
}
