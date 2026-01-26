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
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden" style={{ background: '#FFFFFF' }}>
      {/* Subtle light background gradient */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-[800px] h-[800px] rounded-full bg-gradient-to-br from-indigo-100/40 to-transparent blur-3xl" />
        <div className="absolute -bottom-1/2 -right-1/4 w-[600px] h-[600px] rounded-full bg-gradient-to-tl from-indigo-50/30 to-transparent blur-3xl" />
      </div>

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px)`,
          backgroundSize: '64px 64px'
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-32 text-center">
        {/* Badge */}
        <div className="motion-enter mb-8" style={{ animationDelay: '0s' }}>
          <Badge variant="outline" className="px-4 py-2 text-sm bg-indigo-50 border-indigo-200 text-indigo-600">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse mr-2 inline-block" />
            AI-Powered Marketing Intelligence
          </Badge>
        </div>

        {/* Main headline */}
        <h1 className="motion-enter text-4xl md:text-5xl lg:text-6xl font-bold text-black leading-tight mb-6" style={{ animationDelay: '0.1s' }}>
          Stop Losing{' '}
          <span className="bg-gradient-to-r from-indigo-700 via-indigo-500 to-indigo-600 bg-clip-text text-transparent">
            23% of Ad Spend
          </span>
          {' '}to Bad Attribution
        </h1>

        {/* Subheadline */}
        <p className="motion-enter text-xl md:text-2xl text-gray-600 mb-4" style={{ animationDelay: '0.2s' }}>
          The Revenue Operating System with <strong className="text-black">Trust-Gated Automation</strong>
        </p>

        {/* Description */}
        <p className="motion-enter max-w-2xl mx-auto text-base text-gray-500 mb-8" style={{ animationDelay: '0.3s' }}>
          Brands using Stratum AI recover an average of <strong className="text-gray-700">$24K/month</strong> in wasted ad spend.
          Unify customer data, sync audiences to all ad platforms, and automate only when your signals are healthy.
        </p>

        {/* CTA Buttons */}
        <div className="motion-enter flex flex-col sm:flex-row items-center justify-center gap-4 mb-8" style={{ animationDelay: '0.4s' }}>
          <Button
            onClick={() => navigate('/signup')}
            size="lg"
            className="group text-white font-semibold px-8 py-6 text-lg transition-all hover:scale-[1.02]"
            style={{
              background: 'linear-gradient(135deg, #3730A3 0%, #4F46E5 100%)',
              boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)',
            }}
          >
            14 Day Free Trial
            <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="group border-gray-300 text-black hover:bg-gray-50 px-8 py-6 text-lg"
          >
            <PlayIcon className="w-5 h-5 mr-2" />
            Get Started
          </Button>
        </div>

        {/* Trust Badges */}
        <TooltipProvider>
          <div className="motion-enter flex flex-wrap items-center justify-center gap-6 mb-16" style={{ animationDelay: '0.45s' }}>
            {trustBadges.map((badge, i) => (
              <Tooltip key={i}>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors cursor-default">
                    <CheckIcon className="w-4 h-4 text-indigo-500" />
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
          <div className="relative rounded-2xl overflow-hidden border border-gray-200 shadow-2xl">
            {/* Subtle glow effect behind the preview */}
            <div className="absolute -inset-4 bg-gradient-to-r from-indigo-100/50 to-indigo-50/30 opacity-50 blur-2xl" />

            {/* Dashboard mockup */}
            <div className="relative bg-gray-50 rounded-2xl p-1">
              <div className="bg-white rounded-xl overflow-hidden">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 px-4 py-3 bg-gray-100 border-b border-gray-200">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="px-4 py-1 rounded-md bg-white border border-gray-200 text-xs text-gray-500">
                      app.stratum.ai
                    </div>
                  </div>
                </div>

                {/* Dashboard content preview */}
                <div className="p-6 space-y-4 bg-gray-50">
                  {/* KPI Strip */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {kpis.map((kpi, i) => (
                      <Card key={i} className="bg-white border-gray-200 shadow-sm">
                        <CardContent className="p-4">
                          <div className="text-xs text-gray-500 mb-1">{kpi.label}</div>
                          <div className="text-xl font-semibold text-gray-900">{kpi.value}</div>
                          {kpi.isHealth ? (
                            <div className="mt-2">
                              <Progress value={94} className="h-1.5" />
                            </div>
                          ) : (
                            <div className={`text-xs mt-1 ${kpi.positive ? 'text-green-600' : 'text-red-500'}`}>
                              {kpi.delta}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  {/* Chart placeholder */}
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 h-48 flex items-end gap-1">
                      {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((h, i) => (
                        <div
                          key={i}
                          className="flex-1 bg-gradient-to-t from-indigo-300 to-indigo-500 rounded-t transition-all hover:from-indigo-400 hover:to-indigo-600"
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
          <div className="flex flex-col items-center gap-2 text-gray-400">
            <span className="text-xs">Scroll to explore</span>
            <div className="w-6 h-10 rounded-full border border-gray-300 flex items-start justify-center p-2">
              <div className="w-1 h-2 rounded-full bg-gray-400 animate-bounce" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
