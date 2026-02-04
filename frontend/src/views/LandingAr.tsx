/**
 * Arabic Landing Page
 * Renders the static Arabic landing page HTML in a full-page iframe
 * Includes Voice Greeting and Chat Widget for visitor engagement (Arabic)
 */

import { useState, useEffect } from 'react';
import { OnboardingChat, OnboardingChatButton, VoiceGreeting } from '@/components/onboarding';

export default function LandingAr() {
  const [chatOpen, setChatOpen] = useState(false);
  const [greetingDismissed, setGreetingDismissed] = useState(false);
  const [greetingShown, setGreetingShown] = useState(false);

  // Check if greeting was already shown this session
  useEffect(() => {
    const wasShown = sessionStorage.getItem('stratum_greeting_shown') === 'true';
    setGreetingShown(wasShown);
  }, []);

  const handleStartChat = () => {
    setGreetingDismissed(true);
    setChatOpen(true);
  };

  const handleDismissGreeting = () => {
    setGreetingDismissed(true);
  };

  return (
    <>
      <iframe
        src="/landing-ar.html"
        title="Stratum AI - ذكاء الإيرادات + طبقة الثقة"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          border: 'none',
          margin: 0,
          padding: 0,
          overflow: 'hidden',
        }}
      />

      {/* Voice Greeting - Auto-triggers after 4s or 50% scroll (Arabic) */}
      {!chatOpen && !greetingDismissed && (
        <VoiceGreeting
          triggerDelay={4000}
          triggerScrollPercent={50}
          audioSrc="/audio/greeting-ar.mp3"
          language="ar"
          onStartChat={handleStartChat}
          onDismiss={handleDismissGreeting}
          alreadyShown={greetingShown}
        />
      )}

      {/* Chat Button - Show after greeting is dismissed */}
      {!chatOpen && greetingDismissed && (
        <OnboardingChatButton onClick={() => setChatOpen(true)} pulse={true} />
      )}

      {/* Full Chat Interface (Arabic) */}
      <OnboardingChat isOpen={chatOpen} onClose={() => setChatOpen(false)} language="ar" />
    </>
  );
}
