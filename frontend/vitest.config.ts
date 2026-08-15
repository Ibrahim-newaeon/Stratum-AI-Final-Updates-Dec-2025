import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      // Scope the unit-coverage gate to the modules where unit testing is the
      // right tool and is actually exercised (composed components, contexts,
      // hooks, stores). Page views are validated by the e2e suite; the API
      // client / services layer by integration tests; vendored shadcn/ui is
      // excluded. This keeps the gate meaningful instead of diluting it with
      // hundreds of untested presentational pages.
      include: [
        'src/components/**/*.{ts,tsx}',
        'src/contexts/**/*.{ts,tsx}',
        'src/hooks/**/*.{ts,tsx}',
        'src/stores/**/*.{ts,tsx}',
      ],
      exclude: [
        'src/test/**',
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/components/ui/**',
      ],
      // A regression ratchet, not a target: CI fails if coverage drops below
      // these. Raise them as tests are added; never lower them.
      //
      // Set to the measured coverage on 2026-08-15 (26.04 / 19.75 / 18.12 /
      // 26.86), rounded down to the whole percent. The previous values
      // (23/16/15/24) were the same idea but had drifted 2-3 points below
      // actual, which is enough slack to delete a tested module, or add an
      // untested one, without the gate noticing.
      //
      // The 40% before that was aspirational and unmet, leaving the gate
      // permanently red — which is how a gate stops being read.
      thresholds: {
        statements: 26,
        branches: 19,
        functions: 18,
        lines: 26,
      },
    },
    css: false,
  },
  resolve: {
    alias: {
      // eslint-disable-next-line no-undef
      '@': path.resolve(__dirname, './src'),
    },
  },
});
