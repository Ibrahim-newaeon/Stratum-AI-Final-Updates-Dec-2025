/**
 * Arabic Landing Page
 * Renders the static Arabic landing page HTML in a full-page iframe
 * Includes Chat Widget for visitor engagement (Arabic, click-to-open only)
 */

import { useState } from 'react';
import { OnboardingChat, OnboardingChatButton } from '@/components/onboarding';

export default function LandingAr() {
  const [chatOpen, setChatOpen] = useState(false);

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

      {/* Chat Button - Always visible, opens chat on click */}
      {!chatOpen && (
        <OnboardingChatButton onClick={() => setChatOpen(true)} pulse={true} />
      )}

      {/* Full Chat Interface (Arabic) */}
      <OnboardingChat isOpen={chatOpen} onClose={() => setChatOpen(false)} language="ar" />
    </>
  );
}
