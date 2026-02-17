import { describe, expect, it } from 'vitest';
import {
  calculateChange,
  cn,
  formatCompactNumber,
  formatCurrency,
  formatNumber,
  formatPercent,
  generateId,
  getInitials,
  getPlatformColor,
  truncate,
} from './utils';

describe('cn (className utility)', () => {
  it('should merge class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('should handle conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
  });

  it('should merge tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
  });
});

describe('formatCurrency', () => {
  it('should format USD currency by default', () => {
    const result = formatCurrency(1234.56);
    expect(result).toContain('1,234');
  });

  it('should format whole numbers without decimals', () => {
    const result = formatCurrency(1000);
    expect(result).toContain('1,000');
  });

  it('should handle zero', () => {
    const result = formatCurrency(0);
    expect(result).toContain('0');
  });
});

describe('formatNumber', () => {
  it('should format numbers with thousands separators', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
  });

  it('should format decimal numbers', () => {
    const result = formatNumber(1234.56);
    expect(result).toBe('1,234.56');
  });

  it('should handle zero', () => {
    expect(formatNumber(0)).toBe('0');
  });
});

describe('formatPercent', () => {
  it('should format percentage with default decimals', () => {
    expect(formatPercent(75.5)).toBe('75.5%');
  });

  it('should format percentage with custom decimals', () => {
    expect(formatPercent(75.567, 2)).toBe('75.57%');
  });

  it('should handle zero', () => {
    expect(formatPercent(0)).toBe('0.0%');
  });
});

describe('formatCompactNumber', () => {
  it('should format millions with M suffix', () => {
    expect(formatCompactNumber(1500000)).toBe('1.5M');
  });

  it('should format thousands with K suffix', () => {
    expect(formatCompactNumber(1500)).toBe('1.5K');
  });

  it('should return small numbers as-is', () => {
    expect(formatCompactNumber(999)).toBe('999');
  });

  it('should handle exactly 1 million', () => {
    expect(formatCompactNumber(1000000)).toBe('1M');
  });

  it('should handle exactly 1 thousand', () => {
    expect(formatCompactNumber(1000)).toBe('1K');
  });
});

describe('calculateChange', () => {
  it('should calculate positive change', () => {
    expect(calculateChange(150, 100)).toBe(50);
  });

  it('should calculate negative change', () => {
    expect(calculateChange(50, 100)).toBe(-50);
  });

  it('should return 0 when previous is 0', () => {
    expect(calculateChange(100, 0)).toBe(0);
  });

  it('should return 0 when values are equal', () => {
    expect(calculateChange(100, 100)).toBe(0);
  });
});

describe('getInitials', () => {
  it('should get initials from full name', () => {
    expect(getInitials('John Doe')).toBe('JD');
  });

  it('should handle single name', () => {
    expect(getInitials('John')).toBe('J');
  });

  it('should limit to 2 characters', () => {
    expect(getInitials('John Michael Doe')).toBe('JM');
  });

  it('should uppercase initials', () => {
    expect(getInitials('john doe')).toBe('JD');
  });
});

describe('truncate', () => {
  it('should truncate long strings', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...');
  });

  it('should not truncate short strings', () => {
    expect(truncate('Hello', 10)).toBe('Hello');
  });

  it('should handle exact length', () => {
    expect(truncate('Hello', 5)).toBe('Hello');
  });
});

describe('generateId', () => {
  it('should generate a string', () => {
    const id = generateId();
    expect(typeof id).toBe('string');
  });

  it('should generate unique ids', () => {
    const id1 = generateId();
    const id2 = generateId();
    expect(id1).not.toBe(id2);
  });

  it('should generate ids of expected length', () => {
    const id = generateId();
    expect(id.length).toBe(7);
  });
});

describe('getPlatformColor', () => {
  it('should return correct color for google', () => {
    expect(getPlatformColor('google')).toBe('#4285F4');
  });

  it('should return correct color for meta', () => {
    expect(getPlatformColor('meta')).toBe('#0866FF');
  });

  it('should be case insensitive', () => {
    expect(getPlatformColor('GOOGLE')).toBe('#4285F4');
    expect(getPlatformColor('Meta')).toBe('#0866FF');
  });

  it('should return default color for unknown platforms', () => {
    expect(getPlatformColor('unknown')).toBe('#6B7280');
  });
});
