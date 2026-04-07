/**
 * IdleTimeoutWarning - Modal overlay shown before auto-logout
 *
 * BUG-014: Warns users they will be logged out due to inactivity.
 * Shows a countdown and a "Stay logged in" button.
 */

import { ClockIcon } from '@heroicons/react/24/outline';

interface IdleTimeoutWarningProps {
  secondsLeft: number;
  onStay: () => void;
}

export default function IdleTimeoutWarning({ secondsLeft, onStay }: IdleTimeoutWarningProps) {
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-black/90 border border-white/[0.08] rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl text-center">
        <div className="w-14 h-14 bg-amber-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-amber-500/20">
          <ClockIcon className="w-7 h-7 text-amber-500" />
        </div>

        <h3 className="text-lg font-bold text-white mb-2">Session Expiring</h3>
        <p className="text-sm text-white/50 mb-4">
          You will be logged out in{' '}
          <span className="text-amber-400 font-bold tabular-nums">{secondsLeft}s</span>{' '}
          due to inactivity.
        </p>

        <button
          onClick={onStay}
          className="w-full py-3 px-4 rounded-xl bg-[#00c7be] hover:bg-[#00b3ab] text-black font-bold text-sm transition-colors"
        >
          Stay Logged In
        </button>
      </div>
    </div>
  );
}
