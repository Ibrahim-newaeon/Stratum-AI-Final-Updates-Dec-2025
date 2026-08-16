import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  // Every API client resolves its base URL as
  //   window.__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api/v1'
  // and dist/env-config.js ships as `window.__RUNTIME_CONFIG__ = {}` — it is
  // only populated by the Docker entrypoint, which static hosting (Cloudflare
  // Workers, S3, any CDN) never runs. So with VITE_API_URL unset both overrides
  // are empty, the bundle ships the relative fallback, and every request goes
  // to an origin that serves assets and no API. The site loads perfectly and
  // nothing works — which is why this is worth failing the build over rather
  // than discovering in DevTools.
  if (command === 'build' && mode === 'production' && !process.env.VITE_API_URL) {
    throw new Error(
      '[build] VITE_API_URL is not set. The SPA would fall back to a relative ' +
        '/api/v1 on the static-asset origin and every API call would 404. ' +
        'Set it as a build variable (Cloudflare: Settings -> Variables -> Build).'
    );
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      // Bump from default 500 — vendor-pdf + vendor-charts are large by
      // nature (jsPDF, html2canvas, recharts) and pre-existing. Bumping
      // the warning ceiling so the build log is clean; chunks are still
      // split per the manualChunks below.
      chunkSizeWarningLimit: 700,
      rollupOptions: {
        output: {
          // Function form (not the legacy object map): Vite 8's Rolldown
          // engine only accepts a callback here. Rollup (Vite ≤7) accepts
          // it too, so this is forward- and backward-compatible. The
          // grouping below is unchanged from the previous object map.
          manualChunks(id: string): string | undefined {
            if (!id.includes('node_modules')) return undefined;
            const p = id.replace(/\\/g, '/');
            const group = (pkg: string) => p.includes(`/node_modules/${pkg}/`);
            // PDF stack is route-loaded only by Reporting + Export views;
            // pulling it out of the entry bundle keeps other routes off the
            // ~600kB first-paint hit.
            if (['jspdf', 'html2canvas'].some(group)) return 'vendor-pdf';
            if (['react', 'react-dom', 'react-router-dom'].some(group)) {
              return 'vendor-react';
            }
            if (group('recharts')) return 'vendor-charts';
            if (
              [
                '@radix-ui/react-dialog',
                '@radix-ui/react-dropdown-menu',
                '@radix-ui/react-popover',
                '@radix-ui/react-select',
                '@radix-ui/react-tabs',
                '@radix-ui/react-tooltip',
                '@radix-ui/react-toast',
              ].some(group)
            ) {
              return 'vendor-ui';
            }
            if (group('@tanstack/react-query')) return 'vendor-query';
            if (group('framer-motion')) return 'vendor-motion';
            if (
              [
                '@tiptap/react',
                '@tiptap/starter-kit',
                '@tiptap/extension-image',
                '@tiptap/extension-link',
                '@tiptap/extension-placeholder',
              ].some(group)
            ) {
              return 'vendor-editor';
            }
            if (
              ['i18next', 'react-i18next', 'i18next-browser-languagedetector'].some(
                group,
              )
            ) {
              return 'vendor-i18n';
            }
            if (['react-hook-form', '@hookform/resolvers', 'zod'].some(group)) {
              return 'vendor-forms';
            }
            if (
              ['date-fns', 'clsx', 'tailwind-merge', 'class-variance-authority', 'dompurify'].some(
                group,
              )
            ) {
              return 'vendor-utils';
            }
            return undefined;
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**'],
    },
  };
});
