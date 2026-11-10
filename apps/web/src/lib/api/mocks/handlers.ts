import type { RequestHandler } from 'msw'

/**
 * Browser mocks (VITE_USE_MOCKS=true) for endpoints the API does not have yet. Every endpoint
 * the app uses exists now, so the list is empty; unhandled requests go to the real API.
 */
export const handlers: RequestHandler[] = []
