/**
 * Password Strength Meter Component
 * Visual feedback for password requirements
 */

import { useMemo } from 'react';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface PasswordStrengthProps {
  password: string;
  className?: string;
}

interface PasswordRequirement {
  label: string;
  test: (password: string) => boolean;
}

const requirements: PasswordRequirement[] = [
  { label: 'At least 8 characters', test: (p) => p.length >= 8 },
  { label: 'Contains uppercase letter', test: (p) => /[A-Z]/.test(p) },
  { label: 'Contains lowercase letter', test: (p) => /[a-z]/.test(p) },
  { label: 'Contains a number', test: (p) => /\d/.test(p) },
  { label: 'Contains special character', test: (p) => /[!@#$%^&*(),.?":{}|<>]/.test(p) },
];

function getStrengthLevel(score: number): {
  label: string;
  color: string;
  bgColor: string;
} {
  if (score === 0) return { label: 'Too weak', color: 'text-red-500', bgColor: 'bg-red-500' };
  if (score <= 2) return { label: 'Weak', color: 'text-orange-500', bgColor: 'bg-orange-500' };
  if (score <= 3) return { label: 'Fair', color: 'text-yellow-500', bgColor: 'bg-yellow-500' };
  if (score <= 4) return { label: 'Good', color: 'text-lime-500', bgColor: 'bg-lime-500' };
  return { label: 'Strong', color: 'text-green-500', bgColor: 'bg-green-500' };
}

export function PasswordStrength({ password, className }: PasswordStrengthProps) {
  const { score, results } = useMemo(() => {
    const results = requirements.map((req) => ({
      ...req,
      passed: req.test(password),
    }));
    const score = results.filter((r) => r.passed).length;
    return { score, results };
  }, [password]);

  const strength = getStrengthLevel(score);
  const percentage = (score / requirements.length) * 100;

  if (!password) return null;

  return (
    <div className={cn('space-y-3', className)} role="status" aria-live="polite">
      {/* Strength bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Password strength</span>
          <span className={cn('font-medium', strength.color)}>{strength.label}</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden" role="progressbar" aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100}>
          <div
            className={cn('h-full transition-all duration-300 rounded-full', strength.bgColor)}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* Requirements checklist */}
      <ul className="space-y-1.5" aria-label="Password requirements">
        {results.map((req) => (
          <li
            key={req.label}
            className={cn(
              'flex items-center gap-2 text-xs transition-colors',
              req.passed ? 'text-green-500' : 'text-muted-foreground'
            )}
          >
            {req.passed ? (
              <CheckIcon className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
            ) : (
              <XMarkIcon className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
            )}
            <span>{req.label}</span>
            <span className="sr-only">{req.passed ? '(met)' : '(not met)'}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Compact password strength indicator (just the bar)
 */
export function PasswordStrengthBar({ password, className }: PasswordStrengthProps) {
  const score = useMemo(() => {
    return requirements.filter((req) => req.test(password)).length;
  }, [password]);

  const strength = getStrengthLevel(score);
  const percentage = (score / requirements.length) * 100;

  if (!password) return null;

  return (
    <div className={cn('space-y-1', className)}>
      <div className="h-1 bg-muted rounded-full overflow-hidden" role="progressbar" aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100} aria-label={`Password strength: ${strength.label}`}>
        <div
          className={cn('h-full transition-all duration-300 rounded-full', strength.bgColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={cn('text-xs', strength.color)}>{strength.label}</span>
    </div>
  );
}

export default PasswordStrength;
