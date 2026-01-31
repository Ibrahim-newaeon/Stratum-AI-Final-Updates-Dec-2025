/**
 * Landing Page
 * Renders the static landing page HTML in a full-page iframe
 */

export default function Landing() {
  // Cache-busting: append timestamp to prevent stale content
  const cacheBuster = `?v=${Date.now()}`;

  return (
    <iframe
      src={`/landing.html${cacheBuster}`}
      title="Stratum AI - Revenue Intelligence + Trust Layer"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        border: 'none',
        margin: 0,
        padding: 0,
        overflow: 'hidden',
      }}
    />
  );
}
