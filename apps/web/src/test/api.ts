/** Test doubles for the API: a `fetch` answering from a route table, and a scriptable SSE source. */
import { act } from '@testing-library/react'
import { vi } from 'vitest'
import type { WorkflowEvent } from '@/lib/api/schemas'

export interface Sent {
  method: string
  path: string
  body: unknown
  headers: Record<string, string>
}

export type Routes = Record<string, unknown | (() => unknown)>

/** Keys are `METHOD /path?query`. Unknown routes answer the API's 404 body. Returns the log. */
export function mockApi(routes: Routes): Sent[] {
  const sent: Sent[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input))
      const method = init?.method ?? 'GET'
      const path = url.pathname + url.search
      sent.push({
        method,
        path,
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
        headers: (init?.headers ?? {}) as Record<string, string>,
      })
      const route = routes[`${method} ${path}`]
      if (route === undefined) {
        const error = { error: { code: 'not_found', message: 'Not found', details: {} } }
        return new Response(JSON.stringify(error), { status: 404 })
      }
      const body = typeof route === 'function' ? (route as () => unknown)() : route
      return new Response(JSON.stringify(body), { status: 200 })
    }),
  )
  return sent
}

/** Stand-in for EventSource (jsdom has none); `emit` pushes one SSE message. */
export class FakeEventSource {
  static readonly CLOSED = 2
  static last: FakeEventSource | undefined
  readonly url: string
  readyState = 1
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  private listeners = new Map<string, ((message: MessageEvent<string>) => void)[]>()

  constructor(url: string) {
    this.url = url
    FakeEventSource.last = this
  }
  addEventListener(type: string, listener: (message: MessageEvent<string>) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener])
  }
  close() {
    this.readyState = FakeEventSource.CLOSED
  }
  emit(event: WorkflowEvent) {
    const message = new MessageEvent(event.type, { data: JSON.stringify(event) })
    act(() => this.listeners.get(event.type)?.forEach((listener) => listener(message)))
  }
}
