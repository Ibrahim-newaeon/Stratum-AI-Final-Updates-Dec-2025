/**
 * EmergencyStop — the autopilot kill switch.
 *
 * Operator-triggered emergency stop. Freezing halts ALL autopilot
 * execution for the tenant: the apply-actions worker skips approved
 * actions and the approve/confirm endpoints refuse, so no automation
 * reaches a platform until an operator resumes it. This is distinct from
 * the enforcement guardrails toggle (whose OFF state loosens control) and
 * from the health-derived "frozen" trust-gate mode.
 *
 * Both directions go through a ConfirmDrawer so the stop can't be tripped
 * (or lifted) by a stray click, and both capture an audited reason.
 */

import { useState } from 'react';
import { ShieldAlert, Power } from 'lucide-react';
import { Card } from '@/components/primitives/Card';
import { StatusPill } from '@/components/primitives/StatusPill';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import { useEnforcementSettings, useSetFreeze } from '@/api/autopilot';
import { useToast } from '@/components/ui/use-toast';

interface EmergencyStopProps {
  tenantId: number;
  className?: string;
}

export function EmergencyStop({ tenantId, className }: EmergencyStopProps) {
  const { data, isLoading, isError } = useEnforcementSettings(tenantId);
  const setFreeze = useSetFreeze(tenantId);
  const { toast } = useToast();

  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');

  const frozen = data?.autopilot_frozen ?? false;
  // Freezing is the destructive direction (stops live automation); resuming
  // returns to normal trust-gated operation.
  const nextFrozen = !frozen;

  const handleConfirm = async () => {
    try {
      await setFreeze.mutateAsync({
        frozen: nextFrozen,
        reason: reason.trim() || undefined,
      });
      toast({
        title: nextFrozen ? 'Autopilot frozen' : 'Autopilot resumed',
        description: nextFrozen
          ? 'All automation execution is halted until you resume.'
          : 'Automation resumes under normal trust-gated control.',
      });
      setOpen(false);
      setReason('');
    } catch (error) {
      toast({
        title: 'Could not change state',
        description:
          error instanceof Error ? error.message : 'Failed to toggle the emergency stop.',
        variant: 'destructive',
      });
    }
  };

  return (
    <Card
      variant={frozen ? 'glow' : 'default'}
      className={className}
      data-testid="emergency-stop"
    >
      <div className="p-6 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <ShieldAlert
              aria-hidden="true"
              className={frozen ? 'w-5 h-5 text-danger' : 'w-5 h-5 text-muted-foreground'}
            />
            <h3 className="text-h3 font-medium tracking-tight text-foreground">
              Emergency stop
            </h3>
            <StatusPill
              variant={frozen ? 'unhealthy' : 'healthy'}
              size="sm"
              pulse={frozen}
            >
              {isLoading ? 'Loading' : frozen ? 'Frozen' : 'Active'}
            </StatusPill>
          </div>
          <p className="text-body text-muted-foreground mt-1.5 max-w-prose">
            {isError
              ? 'Could not load the emergency-stop state.'
              : frozen
                ? 'Autopilot is frozen — no automation will execute on any platform until you resume it.'
                : 'Halt all autopilot execution instantly. Approved actions stay queued and resume when you lift the stop.'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setOpen(true)}
          disabled={isLoading || isError || setFreeze.isPending}
          aria-label={frozen ? 'Resume autopilot' : 'Freeze autopilot'}
          className={
            'inline-flex items-center gap-2 rounded-full px-4 py-2 text-meta font-medium flex-shrink-0 ' +
            'transition-all disabled:opacity-50 disabled:cursor-not-allowed ' +
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ' +
            (frozen
              ? 'bg-primary text-primary-foreground hover:brightness-110'
              : 'bg-danger text-white hover:brightness-110')
          }
        >
          <Power className="w-4 h-4" aria-hidden="true" />
          {frozen ? 'Resume autopilot' : 'Freeze autopilot'}
        </button>
      </div>

      <ConfirmDrawer
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o) setReason('');
        }}
        variant={nextFrozen ? 'destructive' : 'default'}
        title={nextFrozen ? 'Freeze all autopilot execution' : 'Resume autopilot'}
        description={
          nextFrozen
            ? 'No approved action will reach any platform until you resume. In-flight approvals are deferred, not cancelled.'
            : 'Autopilot returns to normal trust-gated operation. Deferred approvals will be picked up on the next sweep.'
        }
        confirmLabel={nextFrozen ? 'Freeze autopilot' : 'Resume autopilot'}
        onConfirm={handleConfirm}
        loading={setFreeze.isPending}
      >
        <label className="block">
          <span className="text-meta text-muted-foreground">Reason (optional, audited)</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            placeholder={nextFrozen ? 'e.g. Meta reporting outage' : 'e.g. Incident resolved'}
            className="mt-1.5 w-full rounded-lg bg-card border border-border px-3 py-2 text-body text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
          />
        </label>
      </ConfirmDrawer>
    </Card>
  );
}

export default EmergencyStop;
