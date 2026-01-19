import { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { Badge } from '@/components/ui/badge';
import type { TierContent, TierFAQ as TierFAQType } from '@/config/tierLandingContent';

interface TierFAQProps {
  content: TierContent;
}

function FAQItem({
  faq,
  isOpen,
  onToggle,
  visuals,
}: {
  faq: TierFAQType;
  isOpen: boolean;
  onToggle: () => void;
  visuals: TierContent['visuals'];
}) {
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  return (
    <div className="border-b border-white/5 last:border-0">
      <button
        className="w-full py-6 flex items-start justify-between gap-4 text-left group"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="text-white font-medium group-hover:text-gray-300 transition-colors">
          {faq.question}
        </span>
        <span className={`flex-shrink-0 p-1 rounded-full ${isOpen ? `bg-gradient-to-r ${gradientClass}` : 'bg-white/10'} transition-all`}>
          <ChevronDownIcon
            className={`w-4 h-4 ${isOpen ? 'text-white rotate-180' : 'text-gray-400'} transition-transform duration-200`}
          />
        </span>
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ${
          isOpen ? 'max-h-96 pb-6' : 'max-h-0'
        }`}
      >
        <p className="text-gray-400 leading-relaxed pr-12">
          {faq.answer}
        </p>
      </div>
    </div>
  );
}

export function TierFAQ({ content }: TierFAQProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const { faqs, visuals, name } = content;
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  if (faqs.length === 0) return null;

  return (
    <section className="py-24 bg-surface-primary">
      <div className="max-w-3xl mx-auto px-6">
        {/* Section Header */}
        <div className="text-center mb-12">
          <Badge
            variant="outline"
            className={`mb-4 px-4 py-1 ${visuals.accentColor} border-white/20 bg-white/5`}
          >
            FAQs
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Questions about{' '}
            <span className={`bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
              {name}
            </span>
            ?
          </h2>
          <p className="text-lg text-gray-400">
            Everything you need to know about the {name} plan.
          </p>
        </div>

        {/* FAQ List */}
        <div className="bg-gray-900/30 rounded-2xl border border-white/5 px-6">
          {faqs.map((faq, index) => (
            <FAQItem
              key={index}
              faq={faq}
              isOpen={openIndex === index}
              onToggle={() => setOpenIndex(openIndex === index ? null : index)}
              visuals={visuals}
            />
          ))}
        </div>

        {/* Contact CTA */}
        <div className="mt-12 text-center">
          <p className="text-gray-500 mb-4">
            Still have questions? We're here to help.
          </p>
          <a
            href="/contact"
            className={`inline-flex items-center gap-2 ${visuals.accentColor} hover:underline`}
          >
            Contact our team
            <ChevronDownIcon className="w-4 h-4 -rotate-90" />
          </a>
        </div>
      </div>
    </section>
  );
}
