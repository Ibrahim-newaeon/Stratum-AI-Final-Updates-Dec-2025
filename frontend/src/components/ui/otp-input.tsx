import * as React from 'react';
import { cn } from '@/lib/utils';

interface OTPInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  error?: boolean;
  autoFocus?: boolean;
  className?: string;
}

export function OTPInput({
  length = 6,
  value,
  onChange,
  disabled = false,
  error = false,
  autoFocus = true,
  className,
}: OTPInputProps) {
  const inputRefs = React.useRef<(HTMLInputElement | null)[]>([]);

  // Split value into array of digits
  const digits = value.split('').slice(0, length);
  while (digits.length < length) {
    digits.push('');
  }

  const focusInput = (index: number) => {
    if (index >= 0 && index < length) {
      inputRefs.current[index]?.focus();
    }
  };

  const handleChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value.replace(/\D/g, '');

    if (newValue.length === 0) {
      // Handle delete
      const newDigits = [...digits];
      newDigits[index] = '';
      onChange(newDigits.join(''));
      return;
    }

    if (newValue.length === 1) {
      // Single digit entered
      const newDigits = [...digits];
      newDigits[index] = newValue;
      onChange(newDigits.join(''));

      // Move to next input
      if (index < length - 1) {
        focusInput(index + 1);
      }
    } else if (newValue.length > 1) {
      // Pasted value
      const pastedDigits = newValue.slice(0, length).split('');
      const newDigits = [...digits];

      pastedDigits.forEach((digit, i) => {
        if (index + i < length) {
          newDigits[index + i] = digit;
        }
      });

      onChange(newDigits.join(''));

      // Focus the last filled input or the next empty one
      const lastFilledIndex = Math.min(index + pastedDigits.length - 1, length - 1);
      focusInput(lastFilledIndex);
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (digits[index] === '' && index > 0) {
        // If current is empty, move to previous and delete
        focusInput(index - 1);
        const newDigits = [...digits];
        newDigits[index - 1] = '';
        onChange(newDigits.join(''));
      } else {
        // Delete current
        const newDigits = [...digits];
        newDigits[index] = '';
        onChange(newDigits.join(''));
      }
      e.preventDefault();
    } else if (e.key === 'ArrowLeft' && index > 0) {
      focusInput(index - 1);
      e.preventDefault();
    } else if (e.key === 'ArrowRight' && index < length - 1) {
      focusInput(index + 1);
      e.preventDefault();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    onChange(pastedData);

    // Focus the last input if fully filled, otherwise the next empty one
    if (pastedData.length >= length) {
      focusInput(length - 1);
    } else {
      focusInput(pastedData.length);
    }
  };

  return (
    <div className={cn('flex gap-2 sm:gap-3 justify-center', className)}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => (inputRefs.current[index] = el)}
          type="text"
          inputMode="numeric"
          maxLength={length}
          value={digit}
          onChange={(e) => handleChange(index, e)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={handlePaste}
          disabled={disabled}
          autoFocus={autoFocus && index === 0}
          aria-label={`Digit ${index + 1}`}
          className={cn(
            'w-10 h-12 sm:w-12 sm:h-14 text-center text-xl sm:text-2xl font-semibold',
            'rounded-xl border-2',
            'text-white placeholder-text-muted',
            'transition-all duration-200 outline-none',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
          style={{
            background: 'rgba(255, 255, 255, 0.06)',
            borderColor: error
              ? '#ef4444'
              : digit
                ? 'rgba(252, 100, 35, 0.5)'
                : 'rgba(255, 255, 255, 0.12)',
          }}
          onFocus={(e) => {
            e.target.select();
            e.target.style.borderColor = error ? '#ef4444' : '#FC6423';
            e.target.style.boxShadow = error
              ? '0 0 0 3px rgba(239, 68, 68, 0.1)'
              : '0 0 0 3px rgba(252, 100, 35, 0.1)';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = error
              ? '#ef4444'
              : digit
                ? 'rgba(252, 100, 35, 0.5)'
                : 'rgba(255, 255, 255, 0.12)';
            e.target.style.boxShadow = 'none';
          }}
        />
      ))}
    </div>
  );
}
