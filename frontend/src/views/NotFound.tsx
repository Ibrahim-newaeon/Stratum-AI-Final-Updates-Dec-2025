/**
 * 404 Not Found
 * The trust engine couldn't resolve a route at this address — rendered as
 * a terminal "no signal" readout via the shared ErrorScreen.
 */

import { useLocation, useNavigate } from 'react-router-dom';
import { SEO } from '@/components/common/SEO';
import { ErrorScreen } from '@/components/common/ErrorScreen';

export default function NotFound() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <>
      <SEO
        title="Page Not Found"
        description="The page you're looking for doesn't exist or has been moved."
        noIndex
      />
      <ErrorScreen
        code="404"
        status="No route"
        tone="neutral"
        title="No signal at this address"
        body="The page you're looking for doesn't exist or has been moved. Let's get you back to something live."
        diagnostics={[
          { label: 'Requested', value: pathname || '/' },
          { label: 'Resolution', value: 'no matching route' },
          { label: 'Trust gate', value: 'n/a' },
        ]}
        actions={[
          { label: 'Back to home', to: '/', variant: 'primary' },
          { label: 'Go back', onClick: () => navigate(-1), variant: 'ghost' },
        ]}
        links={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Features', to: '/features' },
          { label: 'Pricing', to: '/pricing' },
          { label: 'Contact', to: '/contact' },
        ]}
      />
    </>
  );
}
