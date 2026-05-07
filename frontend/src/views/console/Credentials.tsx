/**
 * Credentials Health — Platform Owner page at /console/credentials.
 *
 * Reads /superadmin/credentials/health and renders a presence map of
 * every external-service env var the platform expects. No actual
 * values surface — only "set" / "not set". Useful as an
 * "what-do-I-still-need-to-configure" checklist without having to
 * read the Railway env-var screen.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { Card } from '@/components/primitives/Card';
import { CheckCircle2, XCircle, KeyRound } from 'lucide-react';
import { cn } from '@/lib/utils';

type SectionMap = Record<string, Record<string, Record<string, boolean | string | null>>>;
type InfraMap = Record<string, boolean | string | null>;

interface CredentialsHealth {
  ad_platforms: SectionMap['ad_platforms'];
  billing: SectionMap['billing'];
  email: SectionMap['email'];
  ai: SectionMap['ai'];
  infra: InfraMap;
}

function useCredentialsHealth() {
  return useQuery({
    queryKey: ['superadmin-credentials-health'],
    queryFn: async () => {
      const res = await apiClient.get<{ data: CredentialsHealth }>(
        '/superadmin/credentials/health'
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}

export default function ConsoleCredentials() {
  const { data, isPending, error } = useCredentialsHealth();

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight flex items-center gap-2">
          <KeyRound className="w-5 h-5 text-primary" />
          Credentials Health
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Presence-only check across every external-service credential the platform reads
          from settings. No actual secret values are returned — green means the env var
          is set on this deploy, red means it isn't.
        </p>
      </div>

      {isPending && (
        <Card>
          <div className="text-sm text-muted-foreground">Loading credential health…</div>
        </Card>
      )}

      {error && (
        <Card className="border-destructive/30">
          <div className="text-sm text-destructive">
            Couldn't load credentials health: {(error as Error).message}
          </div>
        </Card>
      )}

      {data && (
        <div className="space-y-4">
          <PlatformsSection title="Ad Platforms" sub={data.ad_platforms} />
          <PlatformsSection title="Billing" sub={data.billing} />
          <PlatformsSection title="Email" sub={data.email} />
          <PlatformsSection title="AI" sub={data.ai} />
          <Card>
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-foreground">Infrastructure</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Non-secret config values shown directly, secret presence as boolean.
              </p>
            </div>
            <CredRows fields={data.infra} />
          </Card>
        </div>
      )}
    </div>
  );
}

interface PlatformsSectionProps {
  title: string;
  sub: Record<string, Record<string, boolean | string | null>> | undefined;
}

function PlatformsSection({ title, sub }: PlatformsSectionProps) {
  if (!sub) return null;
  const entries = Object.entries(sub);
  if (entries.length === 0) return null;

  return (
    <Card>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
      </div>
      <div className="space-y-5">
        {entries.map(([providerKey, fields]) => (
          <div key={providerKey}>
            <div className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-2">
              {providerKey.replace(/_/g, ' ')}
            </div>
            <CredRows fields={fields} />
          </div>
        ))}
      </div>
    </Card>
  );
}

function CredRows({ fields }: { fields: Record<string, boolean | string | null> }) {
  const entries = Object.entries(fields);
  return (
    <div className="divide-y divide-border">
      {entries.map(([key, value]) => (
        <div key={key} className="py-2.5 flex items-center justify-between gap-3 first:pt-0 last:pb-0">
          <div className="text-sm font-mono text-foreground/90 truncate">
            {key.replace(/_/g, ' ')}
          </div>
          <div className="flex-shrink-0">
            <Indicator value={value} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Indicator({ value }: { value: boolean | string | null }) {
  if (typeof value === 'string' && value) {
    return (
      <span className="text-xs font-mono text-muted-foreground truncate max-w-xs">
        {value}
      </span>
    );
  }
  if (value === true) {
    return (
      <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium text-success')}>
        <CheckCircle2 className="w-4 h-4" />
        Set
      </span>
    );
  }
  if (value === false || value === null || value === '') {
    return (
      <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium text-destructive')}>
        <XCircle className="w-4 h-4" />
        Not set
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">—</span>;
}
