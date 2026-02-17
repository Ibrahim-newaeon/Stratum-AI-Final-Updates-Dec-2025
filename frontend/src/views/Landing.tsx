import { useEffect } from 'react';

/**
 * Landing page redirect.
 *
 * The primary landing page is a self-contained static HTML file at /landing.html
 * (frontend/public/landing.html). This component redirects to it.
 */
export default function Landing() {
  useEffect(() => {
    window.location.replace('/landing.html');
  }, []);

  return null;
}
