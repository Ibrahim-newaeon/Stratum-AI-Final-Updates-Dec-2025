/**
 * Shared CSS styles for Login & Signup pages
 * Teal-themed glass card design with ambient animations
 */

export const authStyles = `
  /* Floating ambient orbs */
  @keyframes authFloat1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.05); }
    66% { transform: translate(-20px, 20px) scale(0.95); }
  }
  @keyframes authFloat2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(-40px, 30px) scale(1.1); }
    66% { transform: translate(20px, -40px) scale(0.9); }
  }
  @keyframes authFloat3 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(50px, 30px) scale(1.08); }
  }

  .auth-float-1 { animation: authFloat1 20s ease-in-out infinite; }
  .auth-float-2 { animation: authFloat2 25s ease-in-out infinite; }
  .auth-float-3 { animation: authFloat3 18s ease-in-out infinite; }

  /* Fade-up entry animations */
  @keyframes authFadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes authSlideIn {
    from { opacity: 0; transform: translateX(-8px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .auth-fade-up { animation: authFadeUp 0.6s ease-out both; }
  .auth-fade-up-d1 { animation: authFadeUp 0.6s ease-out 0.1s both; }
  .auth-fade-up-d2 { animation: authFadeUp 0.6s ease-out 0.2s both; }
  .auth-fade-up-d3 { animation: authFadeUp 0.6s ease-out 0.3s both; }
  .auth-slide-in { animation: authSlideIn 0.4s ease-out both; }

  /* Glass card */
  .auth-glass-card {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(0, 199, 190, 0.1);
    box-shadow:
      0 24px 48px -12px rgba(0, 0, 0, 0.5),
      0 0 80px -20px rgba(0, 199, 190, 0.06);
  }

  /* Input focus glow */
  .auth-input-glow:focus-within {
    box-shadow: 0 0 0 1px rgba(0, 199, 190, 0.4), 0 0 12px rgba(0, 199, 190, 0.08);
  }

  /* CTA button gradient */
  .auth-gradient-btn {
    background: linear-gradient(135deg, #00c7be 0%, #00a89f 100%);
    box-shadow: 0 4px 20px rgba(0, 199, 190, 0.3);
  }
  .auth-gradient-btn:hover {
    box-shadow: 0 4px 30px rgba(0, 199, 190, 0.45);
  }

  /* Shimmer on hover */
  @keyframes authShimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  .auth-shimmer-btn {
    background: linear-gradient(
      110deg,
      #00c7be 0%,
      #00c7be 40%,
      #66efe8 50%,
      #00c7be 60%,
      #00c7be 100%
    );
    background-size: 200% 100%;
  }
  .auth-shimmer-btn:hover {
    animation: authShimmer 1.5s ease infinite;
  }

  /* Cyber grid background */
  .auth-cyber-grid {
    background-image:
      radial-gradient(circle at 1px 1px, rgba(0, 199, 190, 0.06) 1px, transparent 0);
    background-size: 40px 40px;
  }

  /* Chart bar grow */
  @keyframes authBarGrow {
    from { transform: scaleY(0); }
    to { transform: scaleY(1); }
  }
  .auth-bar-grow {
    animation: authBarGrow 0.8s ease-out both;
    transform-origin: bottom;
  }

  /* Dashboard card chart glow */
  .auth-chart-glow {
    filter: drop-shadow(0 0 8px rgba(0, 199, 190, 0.4));
  }

  /* Gradient text */
  .auth-gradient-text {
    background: linear-gradient(135deg, #00c7be 0%, #e2b347 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
`;
