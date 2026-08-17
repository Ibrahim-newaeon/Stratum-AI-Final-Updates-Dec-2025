import { describe, it, expect } from 'vitest';
import { campaignStatusVariant, campaignStatusLabel } from './statusVariant';

describe('campaignStatusVariant', () => {
  it.each([
    ['active', 'healthy'],
    ['paused', 'degraded'],
    ['draft', 'neutral'],
    ['completed', 'neutral'],
  ] as const)('maps %s to %s', (status, expected) => {
    expect(campaignStatusVariant(status)).toBe(expected);
  });

  it('is case-insensitive', () => {
    expect(campaignStatusVariant('ACTIVE')).toBe('healthy');
  });

  it('falls back to neutral for an unknown status', () => {
    expect(campaignStatusVariant('archived_by_platform')).toBe('neutral');
  });
});

describe('campaignStatusLabel', () => {
  it('capitalises a known status', () => {
    expect(campaignStatusLabel('active')).toBe('Active');
  });

  it('returns unknown statuses unchanged rather than blanking them', () => {
    expect(campaignStatusLabel('archived_by_platform')).toBe('archived_by_platform');
  });
});
