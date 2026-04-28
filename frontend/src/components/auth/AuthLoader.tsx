/**
 * AuthLoader — figma-themed full-screen Suspense fallback for auth routes.
 * Used while /login, /signup, /forgot-password, /verify-email chunks load.
 * Keeps the ink/ember theme cohesive with the landing → form transition.
 */

export default function AuthLoader() {
  return (
    <div
      className="min-h-screen flex items-center justify-center bg-[#0B0B0B] text-white"
      style={{ fontFamily: 'Geist, system-ui, sans-serif' }}
    >
      <div
        className="absolute inset-x-0 top-0 h-72 pointer-events-none"
        style={{
          background:
            'radial-gradient(60% 60% at 50% 0%, rgba(255,90,31,0.16) 0%, rgba(255,90,31,0.04) 40%, transparent 70%)',
        }}
        aria-hidden="true"
      />
      <div className="flex flex-col items-center gap-4 relative z-10">
        <div
          className="w-10 h-10 rounded-full border-2 border-[#1F1F1F] border-t-[#FF5A1F] animate-spin"
          role="status"
          aria-label="Loading"
        />
        <span
          className="text-[11px] uppercase tracking-[0.12em] text-[#6B6B6B]"
          style={{ fontFamily: 'Geist Mono, monospace' }}
        >
          Loading
        </span>
      </div>
    </div>
  );
}
