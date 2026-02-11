/**
 * Voice Greeting Component
 *
 * A greeting popup that auto-triggers after delay or scroll,
 * with optional voice/audio message playback.
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  XMarkIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ChatBubbleLeftRightIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface VoiceGreetingProps {
  /** Delay in ms before auto-showing (default: 4000) */
  triggerDelay?: number;
  /** Scroll percentage to trigger (0-100, default: 50) */
  triggerScrollPercent?: number;
  /** Audio file URL for voice message */
  audioSrc?: string;
  /** Greeting message to display */
  message?: string;
  /** Sub-message or CTA text */
  subMessage?: string;
  /** Language for greeting */
  language?: 'en' | 'ar';
  /** Callback when user wants to start chat */
  onStartChat: () => void;
  /** Callback when dismissed */
  onDismiss?: () => void;
  /** Whether the greeting has already been shown this session */
  alreadyShown?: boolean;
}

const GREETINGS = {
  en: {
    message: "Hi there! 👋 Welcome to Stratum AI",
    subMessage: "I'm here to help you get started with our Revenue Operating System. Want to chat?",
    ctaText: "Let's Talk",
    dismissText: "Maybe Later",
  },
  ar: {
    message: "مرحباً! 👋 أهلاً بك في Stratum AI",
    subMessage: "أنا هنا لمساعدتك في البدء مع نظام تشغيل الإيرادات. هل تريد الدردشة؟",
    ctaText: "لنتحدث",
    dismissText: "ربما لاحقاً",
  },
};

export default function VoiceGreeting({
  triggerDelay = 4000,
  triggerScrollPercent = 50,
  audioSrc,
  message,
  subMessage,
  language = 'en',
  onStartChat,
  onDismiss,
  alreadyShown = false,
}: VoiceGreetingProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasTriggered, setHasTriggered] = useState(alreadyShown);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const texts = GREETINGS[language];
  const displayMessage = message || texts.message;
  const displaySubMessage = subMessage || texts.subMessage;

  // Initialize audio
  useEffect(() => {
    if (audioSrc) {
      audioRef.current = new Audio(audioSrc);
      audioRef.current.addEventListener('ended', () => setIsPlaying(false));
    }
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [audioSrc]);

  // Auto-trigger after delay
  useEffect(() => {
    if (hasTriggered) return;

    const timer = setTimeout(() => {
      if (!hasTriggered) {
        triggerGreeting();
      }
    }, triggerDelay);

    return () => clearTimeout(timer);
  }, [triggerDelay, hasTriggered]);

  // Scroll trigger - listen to iframe scroll
  useEffect(() => {
    if (hasTriggered) return;

    const handleMessage = (event: MessageEvent) => {
      // Listen for scroll events from iframe
      if (event.data?.type === 'scroll' && event.data?.percent >= triggerScrollPercent) {
        if (!hasTriggered) {
          triggerGreeting();
        }
      }
    };

    window.addEventListener('message', handleMessage);

    // Also check if there's a way to detect scroll from parent
    // For iframes, we need postMessage from the iframe content

    return () => window.removeEventListener('message', handleMessage);
  }, [triggerScrollPercent, hasTriggered]);

  const triggerGreeting = () => {
    setHasTriggered(true);
    setIsVisible(true);

    // Auto-play audio if available
    if (audioRef.current && audioSrc) {
      audioRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch(() => {
        // Autoplay blocked - user needs to interact first
        setIsPlaying(false);
      });
    }

    // Store in session that greeting was shown
    sessionStorage.setItem('stratum_greeting_shown', 'true');
  };

  const toggleAudio = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const handleStartChat = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsVisible(false);
    onStartChat();
  };

  const handleDismiss = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsVisible(false);
    onDismiss?.();
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={cn(
            'fixed bottom-24 z-50',
            language === 'ar' ? 'left-4' : 'right-4'
          )}
          dir={language === 'ar' ? 'rtl' : 'ltr'}
        >
          <div className="relative max-w-sm bg-[#0b1215] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
            {/* Gradient top border */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-500" />

            {/* Close button */}
            <button
              onClick={handleDismiss}
              className="absolute top-3 right-3 p-1.5 rounded-full bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors z-10"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>

            {/* Content */}
            <div className="p-5">
              {/* Avatar with pulse animation */}
              <div className="flex items-start gap-4 mb-4">
                <div className="relative">
                  <motion.div
                    animate={isPlaying ? { scale: [1, 1.1, 1] } : {}}
                    transition={{ repeat: Infinity, duration: 1 }}
                    className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center"
                  >
                    <SparklesIcon className="w-6 h-6 text-white" />
                  </motion.div>
                  {/* Speaking indicator */}
                  {isPlaying && (
                    <motion.div
                      animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                      transition={{ repeat: Infinity, duration: 1.5 }}
                      className="absolute inset-0 rounded-full border-2 border-cyan-500"
                    />
                  )}
                </div>
                <div className="flex-1 pt-1">
                  <h4 className="font-semibold text-white text-lg">{displayMessage}</h4>
                </div>
              </div>

              <p className="text-gray-400 text-sm mb-5 leading-relaxed">
                {displaySubMessage}
              </p>

              {/* Audio control (if audio provided) */}
              {audioSrc && (
                <button
                  onClick={toggleAudio}
                  className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors mb-4"
                >
                  {isPlaying ? (
                    <>
                      <SpeakerWaveIcon className="w-4 h-4" />
                      <span>Playing...</span>
                      <motion.div
                        className="flex gap-0.5"
                        animate={{ opacity: [1, 0.5, 1] }}
                        transition={{ repeat: Infinity, duration: 0.8 }}
                      >
                        <span className="w-1 h-3 bg-cyan-500 rounded-full" />
                        <span className="w-1 h-4 bg-cyan-500 rounded-full" />
                        <span className="w-1 h-2 bg-cyan-500 rounded-full" />
                        <span className="w-1 h-3 bg-cyan-500 rounded-full" />
                      </motion.div>
                    </>
                  ) : (
                    <>
                      <SpeakerXMarkIcon className="w-4 h-4" />
                      <span>Play voice message</span>
                    </>
                  )}
                </button>
              )}

              {/* Action buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleStartChat}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-medium rounded-xl hover:opacity-90 transition-opacity"
                >
                  <ChatBubbleLeftRightIcon className="w-5 h-5" />
                  {texts.ctaText}
                </button>
                <button
                  onClick={handleDismiss}
                  className="py-3 px-4 bg-white/5 text-gray-400 font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
                >
                  {texts.dismissText}
                </button>
              </div>
            </div>

            {/* Animated border glow */}
            <motion.div
              animate={{
                boxShadow: [
                  '0 0 20px rgba(0, 199, 190, 0.1)',
                  '0 0 40px rgba(139, 92, 246, 0.15)',
                  '0 0 20px rgba(0, 199, 190, 0.1)',
                ],
              }}
              transition={{ repeat: Infinity, duration: 3 }}
              className="absolute inset-0 rounded-2xl pointer-events-none"
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
