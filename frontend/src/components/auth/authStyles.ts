/**
 * Shared CSS styles for Login & Signup pages
 * Cyberpunk Dark theme — midnight navy + spectral pink/orange/gold
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
    background: rgba(10, 22, 40, 0.8);
    backdrop-filter: blur(25px);
    -webkit-backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
  }

  /* Input focus glow — cyan accent for inputs */
  .auth-input-glow:focus-within {
    box-shadow: 0 0 0 1px rgba(0, 245, 255, 0.4), 0 0 15px rgba(0, 245, 255, 0.15);
  }

  /* CTA button — spectral pink-to-red gradient */
  .auth-gradient-btn {
    background: linear-gradient(135deg, #FF1F6D 0%, #FF3D00 100%);
    box-shadow: 0 0 20px rgba(255, 31, 109, 0.4);
  }
  .auth-gradient-btn:hover {
    box-shadow: 0 0 35px rgba(255, 31, 109, 0.6);
    transform: translateY(-1px);
  }

  /* Shimmer on hover */
  @keyframes authShimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  .auth-shimmer-btn {
    background: linear-gradient(
      110deg,
      #FF1F6D 0%,
      #FF1F6D 40%,
      #FF8C00 50%,
      #FF1F6D 60%,
      #FF1F6D 100%
    );
    background-size: 200% 100%;
  }
  .auth-shimmer-btn:hover {
    animation: authShimmer 1.5s ease infinite;
  }

  /* Mesh background — matching landing page */
  .auth-cyber-grid {
    background-image:
      radial-gradient(circle at 1px 1px, rgba(255, 31, 109, 0.05) 1px, transparent 0);
    background-size: 40px 40px;
    opacity: 0.5;
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
    filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.15));
  }

  /* Gradient text — spectral pink to orange */
  .auth-gradient-text {
    background: linear-gradient(135deg, #FF1F6D 0%, #FF8C00 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* Spectral ring — trust gauge glow */
  .auth-spectral-ring {
    filter: drop-shadow(0 0 12px rgba(255, 31, 109, 0.3));
  }
`;
