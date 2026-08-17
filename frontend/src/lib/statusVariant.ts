/**
 * Domain status -> StatusPill variant.
 *
 * Campaigns.tsx and Rules.tsx each grew their own status badge with their own
 * colours, while StatusPill already existed as a tested primitive. This is the
 * single vocabulary they collapse onto.
 *
 * Deliberately entity-neutral: both screens use active / paused / draft, and
 * campaigns add completed. One mapping, not one per screen — a second copy is
 * how the colours drift apart again.
 *
 * `paused` is degraded (amber) rather than neutral on purpose: amber reads as
 * "not currently delivering", which is what an operator scanning a list needs
 * to catch. draft/completed are neutral — neither implies something is wrong.
 */
import type { StatusPillVariant } from '@/components/primitives/StatusPill';

const STATUS_VARIANT: Record<string, StatusPillVariant> = {
  active: 'healthy',
  paused: 'degraded',
  draft: 'neutral',
  completed: 'neutral',
};

const STATUS_LABEL: Record<string, string> = {
  active: 'Active',
  paused: 'Paused',
  draft: 'Draft',
  completed: 'Completed',
};

/** Unknown statuses fall back to neutral — never throw, never blank the row. */
export function statusVariant(status: string): StatusPillVariant {
  return STATUS_VARIANT[status?.toLowerCase()] ?? 'neutral';
}

/** Unknown statuses are shown verbatim so the operator sees the real value. */
export function statusLabel(status: string): string {
  return STATUS_LABEL[status?.toLowerCase()] ?? status;
}
