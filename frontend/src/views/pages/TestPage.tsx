/**
 * Test Page - Simple page to verify routing works
 */

export default function TestPage() {
  return (
    <div style={{ padding: '20px', background: '#030303', minHeight: '100vh', color: 'white' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '20px' }}>Test Page Works!</h1>
      <p>If you can see this page, React Router is working correctly.</p>
      <p style={{ marginTop: '20px', color: '#888' }}>Route: /test-page</p>
    </div>
  );
}
