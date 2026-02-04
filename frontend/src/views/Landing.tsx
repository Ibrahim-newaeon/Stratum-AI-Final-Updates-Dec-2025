/**
 * Landing Page
 * Renders the static landing page HTML in a full-page iframe
 * Includes Voice Greeting and Chat Widget for visitor engagement
 */

import { useState, useEffect } from 'react';
import { OnboardingChat, OnboardingChatButton, VoiceGreeting } from '@/components/onboarding';

export default function Landing() {
  // Cache-busting: append timestamp to prevent stale content
  const cacheBuster = `?v=${Date.now()}`;
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
        src={`/landing.html${cacheBuster}`}
        title="Stratum AI - Revenue Intelligence + Trust Layer"
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

      {/* Voice Greeting - Auto-triggers after 4s or 50% scroll */}
      {!chatOpen && !greetingDismissed && (
        <VoiceGreeting
          triggerDelay={4000}
          triggerScrollPercent={50}
          audioSrc="/audio/greeting-en.mp3"
          language="en"
          onStartChat={handleStartChat}
          onDismiss={handleDismissGreeting}
          alreadyShown={greetingShown}
        />
      )}

      {/* Chat Button - Show after greeting is dismissed */}
      {!chatOpen && greetingDismissed && (
        <OnboardingChatButton onClick={() => setChatOpen(true)} pulse={true} />
      )}

      {/* Full Chat Interface */}
      <OnboardingChat isOpen={chatOpen} onClose={() => setChatOpen(false)} language="en" />
    </>
  );
}
