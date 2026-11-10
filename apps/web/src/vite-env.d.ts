/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_USE_MOCKS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** Set by `/config.js` before the app loads; the Docker image writes it at container start. */
interface OrchestraiRuntimeConfig {
  readonly apiUrl?: string
}

interface Window {
  readonly __ORCHESTRAI_CONFIG__?: OrchestraiRuntimeConfig
}
