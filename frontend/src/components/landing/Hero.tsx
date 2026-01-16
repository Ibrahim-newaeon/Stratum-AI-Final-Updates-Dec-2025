import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, PlayIcon, CheckIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

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
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-surface-primary">
      {/* Background gradient effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-[800px] h-[800px] rounded-full bg-gradient-to-br from-stratum-500/20 to-transparent blur-3xl" />
        <div className="absolute -bottom-1/2 -right-1/4 w-[600px] h-[600px] rounded-full bg-gradient-to-tl from-cyan-500/15 to-transparent blur-3xl" />
        <div className="absolute top-1/4 right-1/3 w-[400px] h-[400px] rounded-full bg-stratum-500/5 blur-2xl" />
      </div>

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '64px 64px'
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-32 text-center">
        {/* Badge */}
        <div className="motion-enter mb-8" style={{ animationDelay: '0s' }}>
          <Badge variant="outline" className="px-4 py-2 text-sm bg-stratum-500/10 border-stratum-500/20 text-stratum-400">
            <span className="w-2 h-2 rounded-full bg-stratum-500 animate-pulse mr-2 inline-block" />
            AI-Powered Marketing Intelligence
          </Badge>
        </div>

        {/* Main headline */}
        <h1 className="motion-enter text-4xl md:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6" style={{ animationDelay: '0.1s' }}>
          Stop Losing{' '}
          <span className="bg-gradient-to-r from-orange-500 via-red-500 to-blue-500 bg-clip-text text-transparent">
            23% of Ad Spend
          </span>
          {' '}to Bad Attribution
        </h1>

        {/* Subheadline */}
        <p className="motion-enter text-xl md:text-2xl text-gray-400 mb-4" style={{ animationDelay: '0.2s' }}>
          The Revenue Operating System with <strong className="text-white">Trust-Gated Automation</strong>
        </p>

        {/* Description */}
        <p className="motion-enter max-w-2xl mx-auto text-base text-gray-500 mb-8" style={{ animationDelay: '0.3s' }}>
          Brands using Stratum AI recover an average of <strong className="text-gray-300">$24K/month</strong> in wasted ad spend.
          Unify customer data, sync audiences to all ad platforms, and automate only when your signals are healthy.
        </p>

        {/* CTA Buttons */}
        <div className="motion-enter flex flex-col sm:flex-row items-center justify-center gap-4 mb-8" style={{ animationDelay: '0.4s' }}>
          <Button
            onClick={() => navigate('/signup')}
            size="lg"
            className="group bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white font-semibold px-8 py-6 text-lg shadow-lg shadow-orange-500/30 hover:shadow-orange-500/50 transition-all"
          >
            Get Early Access
            <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="group border-white/20 text-white hover:bg-white/10 px-8 py-6 text-lg"
          >
            <PlayIcon className="w-5 h-5 mr-2" />
            Book Demo
          </Button>
        </div>

        {/* Trust Badges */}
        <TooltipProvider>
          <div className="motion-enter flex flex-wrap items-center justify-center gap-6 mb-16" style={{ animationDelay: '0.45s' }}>
            {trustBadges.map((badge, i) => (
              <Tooltip key={i}>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 text-gray-400 hover:text-gray-300 transition-colors cursor-default">
                    <CheckIcon className="w-4 h-4 text-green-500" />
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
          <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
            {/* Glow effect behind the preview */}
            <div className="absolute -inset-4 bg-gradient-to-r from-orange-500/20 to-blue-500/20 opacity-50 blur-2xl" />

            {/* Dashboard mockup */}
            <div className="relative bg-gray-900/80 backdrop-blur rounded-2xl p-1">
              <div className="bg-gray-950 rounded-xl overflow-hidden">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 px-4 py-3 bg-gray-900 border-b border-white/5">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="px-4 py-1 rounded-md bg-gray-800 text-xs text-gray-400">
                      app.stratum.ai
                    </div>
                  </div>
                </div>

                {/* Dashboard content preview */}
                <div className="p-6 space-y-4">
                  {/* KPI Strip */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {kpis.map((kpi, i) => (
                      <Card key={i} className="bg-gray-900/50 border-white/5">
                        <CardContent className="p-4">
                          <div className="text-xs text-gray-500 mb-1">{kpi.label}</div>
                          <div className="text-xl font-semibold text-white">{kpi.value}</div>
                          {kpi.isHealth ? (
                            <div className="mt-2">
                              <Progress value={94} className="h-1.5" />
                            </div>
                          ) : (
                            <div className={`text-xs mt-1 ${kpi.positive ? 'text-green-500' : 'text-red-500'}`}>
                              {kpi.delta}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  {/* Chart placeholder */}
                  <Card className="bg-gray-900/50 border-white/5">
                    <CardContent className="p-4 h-48 flex items-end gap-1">
                      {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((h, i) => (
                        <div
                          key={i}
                          className="flex-1 bg-gradient-to-t from-orange-500/40 to-orange-500/80 rounded-t transition-all hover:from-orange-500/60 hover:to-orange-500"
                          style={{ height: `${h}%` }}
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
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 motion-enter" style={{ animationDelay: '0.6s' }}>
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <span className="text-xs">Scroll to explore</span>
            <div className="w-6 h-10 rounded-full border border-white/20 flex items-start justify-center p-2">
              <div className="w-1 h-2 rounded-full bg-white/40 animate-bounce" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
