/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL?: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_SENTRY_DEBUG?: string
  readonly MODE: string
  readonly DEV: boolean
  readonly PROD: boolean
  readonly SSR: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** Runtime configuration injected at deploy time */
interface RuntimeConfig {
  VITE_API_URL?: string
  VITE_WS_URL?: string
  [key: string]: string | undefined
}

interface Window {
  __RUNTIME_CONFIG__?: RuntimeConfig
}
