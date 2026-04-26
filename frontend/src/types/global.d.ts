/**
 * Global type declarations for runtime-injected values
 */

interface RuntimeConfig {
  VITE_API_URL?: string;
  VITE_WS_URL?: string;
  VITE_ENABLE_DEMO_MODE?: string;
}

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: RuntimeConfig;
  }
}

export {};
