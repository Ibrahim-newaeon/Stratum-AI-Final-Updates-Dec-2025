import { describe, it, expect } from 'vitest';
import { statusVariant, statusLabel } from './statusVariant';

describe('statusVariant', () => {
  it.each([
    ['active', 'healthy'],
    ['paused', 'degraded'],
    ['draft', 'neutral'],
    ['completed', 'neutral'],
  ] as const)('maps %s to %s', (status, expected) => {
    expect(statusVariant(status)).toBe(expected);
  });

  it('is case-insensitive', () => {
    expect(statusVariant('ACTIVE')).toBe('healthy');
  });

  it('falls back to neutral for an unknown status', () => {
    expect(statusVariant('archived_by_platform')).toBe('neutral');
  });

  it('serves campaigns and rules from one vocabulary', () => {
    // Rules use active/paused/draft; campaigns add completed. Both previously
    // shipped their own badge with their own colours — collapsing them onto one
    // mapping is the point of this module, so the shared statuses are pinned
    // here rather than asserted separately per screen.
    expect(statusVariant('active')).toBe('healthy');
    expect(statusVariant('paused')).toBe('degraded');
    expect(statusVariant('draft')).toBe('neutral');
  });
});

describe('statusLabel', () => {
  it('capitalises a known status', () => {
    expect(statusLabel('active')).toBe('Active');
  });

  it('returns unknown statuses unchanged rather than blanking them', () => {
    expect(statusLabel('archived_by_platform')).toBe('archived_by_platform');
  });
});
