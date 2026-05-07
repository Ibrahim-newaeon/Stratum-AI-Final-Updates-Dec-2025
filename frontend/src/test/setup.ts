import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Auto-unmount React Testing Library trees after each test. Without
// this, every render() leaves its DOM in document.body and event
// listeners + reconciler state accumulate across the file. The
// 14 component tests in ProtectedRoute.test.tsx OOM'd the worker
// before this was wired (passes individually, hangs together).
afterEach(() => {
  cleanup();
});
