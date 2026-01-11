/**
 * Arabic Landing Page
 * Renders the static Arabic landing page HTML in a full-page iframe
 */

export default function LandingAr() {
  return (
    <iframe
      src="/landing-ar.html"
      title="Stratum AI - ذكاء الإيرادات + طبقة الثقة"
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
