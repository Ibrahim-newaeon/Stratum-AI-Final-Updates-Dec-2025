/**
 * 403 Access Denied
 * Shown when an authenticated user lacks the role/permission for a route.
 * Leans into Stratum's own vocabulary — the trust gate returned BLOCKED.
 *
 * ProtectedRoute redirects here on role/portal violations, so this page must
 * NOT be auth-gated (that would loop). It is intentionally a sibling route.
 */

import { useLocation, useNavigate } from 'react-router-dom';
import { SEO } from '@/components/common/SEO';
import { ErrorScreen } from '@/components/common/ErrorScreen';

export default function Unauthorized() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <>
      <SEO
        title="Access Denied"
        description="You don't have permission to view this page."
        noIndex
      />
      <ErrorScreen
        code="403"
        status="Gate · Blocked"
        tone="blocked"
        title="Access gated"
        body="You don't have clearance for this page. If you think that's wrong, your workspace administrator can adjust your role."
        diagnostics={[
          { label: 'Requested', value: pathname || '/' },
          { label: 'Clearance', value: 'insufficient' },
          { label: 'Trust gate', value: 'BLOCKED', emphasis: 'blocked' },
        ]}
        actions={[
          { label: 'Back to dashboard', to: '/dashboard', variant: 'primary' },
          { label: 'Go back', onClick: () => navigate(-1), variant: 'ghost' },
        ]}
        links={[
          { label: 'Account settings', to: '/dashboard/settings/profile' },
          { label: 'Contact support', to: '/contact' },
        ]}
      />
    </>
  );
}
