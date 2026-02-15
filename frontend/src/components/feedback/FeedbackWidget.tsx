/**
 * FeedbackWidget - In-app feedback floating button + panel
 *
 * Self-contained component: floating teal/gold button that opens a
 * feedback panel with emoji rating, category pills, and a comment box.
 * Stores feedback in localStorage and shows a toast on submit.
 */

import { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  MessageSquarePlus,
  X,
  Bug,
  Sparkles,
  MessageCircle,
  Send,
  Heart,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

/* ------------------------------------------------------------------ */
/*  Types & constants                                                  */
/* ------------------------------------------------------------------ */

interface FeedbackEntry {
  rating: number;
  category: string;
  comment: string;
  timestamp: string;
  page: string;
}

const STORAGE_KEY = 'stratum-feedback';

const ratings = [
  { value: 1, emoji: '\u{1F61E}', label: 'Terrible' },
  { value: 2, emoji: '\u{1F615}', label: 'Bad' },
  { value: 3, emoji: '\u{1F610}', label: 'Okay' },
  { value: 4, emoji: '\u{1F60A}', label: 'Good' },
  { value: 5, emoji: '\u{1F929}', label: 'Amazing' },
];

const categories = [
  { value: 'bug', label: 'Bug Report', icon: Bug },
  { value: 'feature', label: 'Feature Request', icon: Sparkles },
  { value: 'general', label: 'General', icon: MessageCircle },
] as const;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function FeedbackWidget() {
  const { toast } = useToast();
  const [isOpen, setIsOpen] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [comment, setComment] = useState('');

  /* ---------- Escape-key handler ---------- */
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen]);

  /* ---------- Submit ---------- */
  const handleSubmit = useCallback(() => {
    if (!rating) return;

    const feedback: FeedbackEntry = {
      rating,
      category: category || 'general',
      comment: comment.trim(),
      timestamp: new Date().toISOString(),
      page: window.location.pathname,
    };

    // Persist locally (for future backend sync)
    try {
      const existing: FeedbackEntry[] = JSON.parse(
        localStorage.getItem(STORAGE_KEY) || '[]',
      );
      existing.push(feedback);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
    } catch {
      // Silently ignore storage errors
    }

    toast({
      title: 'Thank you for your feedback!',
      description: 'Your input helps us improve Stratum AI.',
    });

    // Reset & close
    setRating(null);
    setCategory(null);
    setComment('');
    setIsOpen(false);
  }, [rating, category, comment, toast]);

  /* ---------- Render ---------- */
  return (
    <>
      {/* ---- Floating trigger button ---- */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            key="feedback-btn"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            whileHover={{ scale: 1.12 }}
            whileTap={{ scale: 0.92 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-20 right-4 w-12 h-12 rounded-full text-white shadow-lg hover:shadow-xl transition-shadow z-40 flex items-center justify-center"
            style={{
              background:
                'linear-gradient(135deg, #00c7be 0%, #e2b347 100%)',
              boxShadow: '0 0 25px rgba(0, 199, 190, 0.3)',
            }}
            title="Send Feedback"
            aria-label="Open feedback form"
          >
            <MessageSquarePlus className="w-5 h-5" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* ---- Feedback panel ---- */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="feedback-panel"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 350, damping: 28 }}
            className="fixed bottom-20 right-4 w-[380px] max-h-[520px] rounded-2xl border border-[#00c7be]/20 shadow-2xl flex flex-col overflow-hidden z-50"
            style={{
              background: '#0b1215',
              boxShadow:
                '0 0 40px rgba(0, 199, 190, 0.15), 0 8px 32px rgba(0,0,0,0.4)',
              backdropFilter: 'blur(40px) saturate(1.8)',
            }}
          >
            {/* ---- Header ---- */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#00c7be]/15 bg-gradient-to-r from-[#00c7be]/10 to-transparent">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#00c7be]/15 flex items-center justify-center">
                  <Heart className="w-4 h-4 text-[#00c7be]" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Send Feedback
                  </h3>
                  <p className="text-[11px] text-white/40">
                    Help us improve Stratum AI
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors"
                aria-label="Close feedback"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* ---- Body (scrollable) ---- */}
            <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
              {/* Rating */}
              <div>
                <label className="block text-xs font-medium text-white/50 mb-3">
                  How's your experience?{' '}
                  <span className="text-[#00c7be]">*</span>
                </label>
                <div className="flex justify-center gap-3">
                  {ratings.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setRating(r.value)}
                      className={cn(
                        'flex flex-col items-center gap-1.5 p-2.5 rounded-xl transition-all duration-200',
                        rating === r.value
                          ? 'bg-[#00c7be]/15 ring-2 ring-[#00c7be]/40 scale-110'
                          : 'opacity-50 hover:opacity-100 hover:bg-white/5',
                      )}
                      aria-label={r.label}
                    >
                      <span className="text-2xl leading-none">
                        {r.emoji}
                      </span>
                      <span
                        className="text-[10px] font-medium"
                        style={{
                          color:
                            rating === r.value
                              ? '#00c7be'
                              : 'rgba(245,245,247,0.35)',
                        }}
                      >
                        {r.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Category */}
              <div>
                <label className="block text-xs font-medium text-white/50 mb-3">
                  Category{' '}
                  <span className="text-white/25">(optional)</span>
                </label>
                <div className="flex gap-2">
                  {categories.map((cat) => {
                    const Icon = cat.icon;
                    return (
                      <button
                        key={cat.value}
                        onClick={() =>
                          setCategory(
                            category === cat.value ? null : cat.value,
                          )
                        }
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border',
                          category === cat.value
                            ? 'bg-[#00c7be]/15 border-[#00c7be]/40 text-[#00c7be]'
                            : 'bg-transparent border-white/10 text-white/40 hover:border-white/20 hover:text-white/60',
                        )}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        {cat.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Comment */}
              <div>
                <label className="block text-xs font-medium text-white/50 mb-3">
                  Tell us more{' '}
                  <span className="text-white/25">(optional)</span>
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="What can we do better?"
                  rows={3}
                  className="w-full bg-[rgba(255,255,255,0.05)] border border-[#00c7be]/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/25 focus:outline-none focus:border-[#00c7be]/40 transition-colors resize-none"
                />
              </div>
            </div>

            {/* ---- Footer / Submit ---- */}
            <div className="px-5 pb-5 pt-2">
              <button
                onClick={handleSubmit}
                disabled={!rating}
                className={cn(
                  'w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold transition-all',
                  rating
                    ? 'bg-[#00c7be] hover:bg-[#00b3ab] text-[#0b1215] shadow-[0_0_20px_rgba(0,199,190,0.3)]'
                    : 'bg-white/5 text-white/25 cursor-not-allowed',
                )}
              >
                <Send className="w-4 h-4" />
                Submit Feedback
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default FeedbackWidget;
