import { StarIcon, BuildingOffice2Icon, UsersIcon } from '@heroicons/react/24/solid';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { TierContent, TierTestimonial } from '@/config/tierLandingContent';

interface TierTestimonialsProps {
  content: TierContent;
}

function TestimonialCard({
  testimonial,
  visuals,
}: {
  testimonial: TierTestimonial;
  visuals: TierContent['visuals'];
}) {
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  return (
    <Card className="bg-gray-900/50 border-white/5 hover:border-white/10 transition-all">
      <CardContent className="p-6">
        {/* Stars */}
        <div className="flex gap-1 mb-4">
          {[1, 2, 3, 4, 5].map((star) => (
            <StarIcon key={star} className={`w-4 h-4 text-amber-400`} />
          ))}
        </div>

        {/* Quote */}
        <blockquote className="text-white text-base leading-relaxed mb-6">
          "{testimonial.quote}"
        </blockquote>

        {/* Author Info */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Avatar placeholder */}
            <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${gradientClass} flex items-center justify-center text-white font-bold text-lg`}>
              {testimonial.author.charAt(0)}
            </div>
            <div>
              <div className="text-white font-medium">{testimonial.author}</div>
              <div className="text-sm text-gray-500">{testimonial.role}</div>
              <div className="flex items-center gap-2 mt-1">
                <BuildingOffice2Icon className="w-3 h-3 text-gray-600" />
                <span className="text-xs text-gray-600">{testimonial.company}</span>
                <span className="text-gray-700">·</span>
                <UsersIcon className="w-3 h-3 text-gray-600" />
                <span className="text-xs text-gray-600">{testimonial.companySize}</span>
              </div>
            </div>
          </div>

          {/* Metric Badge */}
          {testimonial.metric && (
            <div className="text-right">
              <div className={`text-xl font-bold bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
                {testimonial.metric.value}
              </div>
              <div className="text-xs text-gray-500">{testimonial.metric.label}</div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function TierTestimonials({ content }: TierTestimonialsProps) {
  const { testimonials, visuals, name } = content;
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  if (testimonials.length === 0) return null;

  return (
    <section className="py-24 bg-surface-primary">
      <div className="max-w-6xl mx-auto px-6">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge
            variant="outline"
            className={`mb-4 px-4 py-1 ${visuals.accentColor} border-white/20 bg-white/5`}
          >
            Customer Stories
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Loved by{' '}
            <span className={`bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
              {name}
            </span>
            {' '}customers
          </h2>
          <p className="text-lg text-gray-400 max-w-xl mx-auto">
            See how teams like yours are getting results with Stratum AI.
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className={`grid gap-6 ${testimonials.length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-3'}`}>
          {testimonials.map((testimonial, index) => (
            <TestimonialCard
              key={index}
              testimonial={testimonial}
              visuals={visuals}
            />
          ))}
        </div>

        {/* Stats Summary */}
        <div className="mt-16 flex flex-wrap justify-center gap-8 md:gap-16">
          {[
            { value: '150+', label: 'Growth teams' },
            { value: '$12M+', label: 'Ad spend optimized' },
            { value: '4.2x', label: 'Average ROAS' },
          ].map((stat, i) => (
            <div key={i} className="text-center">
              <div className={`text-3xl md:text-4xl font-bold bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
                {stat.value}
              </div>
              <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
