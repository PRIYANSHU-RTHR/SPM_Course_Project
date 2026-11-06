import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from '@/app/App'
import './index.css'

async function enableMocks() {
  if (import.meta.env.VITE_USE_MOCKS !== 'true') return
  const { worker } = await import('@/lib/api/mocks/browser')
  await worker.start({ onUnhandledFrame: 'bypass', quiet: true })
}

// Failed mocks must not leave a blank page: the app still starts against the real API.
void enableMocks()
  .catch((error: unknown) => console.error('Mocks did not start', error))
  .finally(() => {
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
