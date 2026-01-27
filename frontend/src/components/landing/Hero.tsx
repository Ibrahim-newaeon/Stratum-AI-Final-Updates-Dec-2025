import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, CheckIcon, PlayIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export function Hero() {
  const navigate = useNavigate();

  const kpis = [
    { label: 'Total Spend', value: '$124,580', delta: '+12.4%', positive: true },
    { label: 'Revenue', value: '$892,340', delta: '+28.7%', positive: true },
    { label: 'Blended ROAS', value: '7.16x', delta: '+0.42', positive: true },
    { label: 'Signal Health', value: '94', delta: 'Reliable', positive: true, isHealth: true },
  ];

  const trustBadges = [
    { text: '150+ growth teams', icon: '✓' },
    { text: '$12M+ recovered', icon: '✓' },
    { text: '4.2x avg ROAS', icon: '✓' },
  ];

  return (
    <section
      className="relative min-h-screen flex items-center justify-center overflow-hidden"
      style={{ background: '#000000' }}
    >
      {/* Ambient orbs - Apple Glass Dark */}
      <div className="absolute inset-0 overflow-hidden">
        <div
          className="absolute -top-1/4 -left-1/4 w-[800px] h-[800px] rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(10, 132, 255, 0.08), transparent 60%)' }}
        />
        <div
          className="absolute -bottom-1/4 -right-1/4 w-[600px] h-[600px] rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(191, 90, 242, 0.06), transparent 60%)' }}
        />
        <div
          className="absolute top-1/3 right-1/4 w-[500px] h-[500px] rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(100, 210, 255, 0.05), transparent 60%)' }}
        />
      </div>

      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-32 text-center">
        {/* Badge */}
        <div className="motion-enter mb-8" style={{ animationDelay: '0s' }}>
          <Badge
            variant="outline"
            className="px-4 py-2 text-sm border-0"
            style={{
              background: 'rgba(10, 132, 255, 0.15)',
              color: '#0A84FF',
            }}
          >
            <span className="w-2 h-2 rounded-full animate-pulse mr-2 inline-block" style={{ background: '#0A84FF' }} />
            AI-Powered Marketing Intelligence
          </Badge>
        </div>

        {/* Main headline */}
        <h1
          className="motion-enter text-4xl md:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6"
          style={{ animationDelay: '0.1s' }}
        >
          Stop Losing{' '}
          <span style={{ color: '#0A84FF' }}>23% of Ad Spend</span>{' '}
          to Bad Attribution
        </h1>

        {/* Subheadline */}
        <p
          className="motion-enter text-xl md:text-2xl mb-4"
          style={{ animationDelay: '0.2s', color: 'rgba(255, 255, 255, 0.7)' }}
        >
          The Revenue Operating System with{' '}
          <strong className="text-white">Trust-Gated Automation</strong>
        </p>

        {/* Description */}
        <p
          className="motion-enter max-w-2xl mx-auto text-base mb-8"
          style={{ animationDelay: '0.3s', color: 'rgba(255, 255, 255, 0.5)' }}
        >
          Brands using Stratum AI recover an average of{' '}
          <strong style={{ color: 'rgba(255, 255, 255, 0.7)' }}>$24K/month</strong> in wasted ad spend. Unify customer
          data, sync audiences to all ad platforms, and automate only when your signals are healthy.
        </p>

        {/* CTA Buttons */}
        <div
          className="motion-enter flex flex-col sm:flex-row items-center justify-center gap-4 mb-8"
          style={{ animationDelay: '0.4s' }}
        >
          <Button
            onClick={() => navigate('/signup')}
            size="lg"
            className="group text-white font-semibold px-8 py-6 text-lg transition-all hover:scale-[1.02] rounded-2xl"
            style={{
              background: '#0A84FF',
              boxShadow: '0 0 40px rgba(10, 132, 255, 0.25)',
            }}
          >
            14 Day Free Trial
            <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="group px-8 py-6 text-lg rounded-2xl"
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              backdropFilter: 'blur(40px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: '#ffffff',
            }}
          >
            <PlayIcon className="w-5 h-5 mr-2" />
            Get Started
          </Button>
        </div>

        {/* Trust Badges */}
        <TooltipProvider>
          <div
            className="motion-enter flex flex-wrap items-center justify-center gap-6 mb-16"
            style={{ animationDelay: '0.45s' }}
          >
            {trustBadges.map((badge, i) => (
              <Tooltip key={i}>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 transition-colors cursor-default" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    <CheckIcon className="w-4 h-4" style={{ color: '#30D158' }} />
                    <span className="text-sm">{badge.text}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Verified metric from 2023-2025</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </TooltipProvider>

        {/* Dashboard Preview */}
        <div className="motion-enter relative max-w-5xl mx-auto" style={{ animationDelay: '0.5s' }}>
          <div
            className="relative rounded-3xl overflow-hidden"
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              boxShadow: '0 0 60px rgba(10, 132, 255, 0.15)',
            }}
          >
            {/* Dashboard mockup */}
            <div className="relative rounded-3xl p-1">
              <div className="rounded-2xl overflow-hidden">
                {/* Browser chrome */}
                <div
                  className="flex items-center gap-2 px-4 py-3"
                  style={{
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#FF453A' }} />
                    <div className="w-3 h-3 rounded-full" style={{ background: '#FFD60A' }} />
                    <div className="w-3 h-3 rounded-full" style={{ background: '#30D158' }} />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div
                      className="px-4 py-1 rounded-full text-xs"
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        color: 'rgba(255, 255, 255, 0.5)',
                      }}
                    >
                      app.stratum.ai
                    </div>
                  </div>
                </div>

                {/* Dashboard content preview */}
                <div className="p-6 space-y-4" style={{ background: 'rgba(0, 0, 0, 0.3)' }}>
                  {/* KPI Strip */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {kpis.map((kpi, i) => (
                      <Card
                        key={i}
                        className="border-0"
                        style={{
                          background: 'rgba(255, 255, 255, 0.03)',
                          backdropFilter: 'blur(20px)',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                        }}
                      >
                        <CardContent className="p-4">
                          <div className="text-xs mb-1" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>{kpi.label}</div>
                          <div className="text-xl font-semibold text-white">{kpi.value}</div>
                          {kpi.isHealth ? (
                            <div className="mt-2">
                              <Progress value={94} className="h-1.5" />
                            </div>
                          ) : (
                            <div
                              className="text-xs mt-1"
                              style={{ color: kpi.positive ? '#30D158' : '#FF453A' }}
                            >
                              {kpi.delta}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  {/* Chart placeholder */}
                  <Card
                    className="border-0"
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      backdropFilter: 'blur(20px)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                    }}
                  >
                    <CardContent className="p-4 h-48 flex items-end gap-1">
                      {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((h, i) => (
                        <div
                          key={i}
                          className="flex-1 rounded-t transition-all"
                          style={{
                            height: `${h}%`,
                            background: 'linear-gradient(to top, rgba(10, 132, 255, 0.4), rgba(10, 132, 255, 0.8))',
                          }}
                        />
                      ))}
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 motion-enter"
          style={{ animationDelay: '0.6s' }}
        >
          <div className="flex flex-col items-center gap-2" style={{ color: 'rgba(255, 255, 255, 0.4)' }}>
            <span className="text-xs">Scroll to explore</span>
            <div
              className="w-6 h-10 rounded-full flex items-start justify-center p-2"
              style={{ border: '1px solid rgba(255, 255, 255, 0.2)' }}
            >
              <div className="w-1 h-2 rounded-full animate-bounce" style={{ background: 'rgba(255, 255, 255, 0.4)' }} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
