// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { WorkflowEvent, WorkflowState } from '@/lib/api/schemas'
import { NewPlanPage } from './NewPlanPage'
import { EXAMPLE, REVIEW, runState, SKILLS } from './plan.fixtures'
import { PlanRunPage } from './PlanRunPage'

interface Sent {
  method: string
  path: string
  body: unknown
  headers: Record<string, string>
}

/** `fetch` answering from a route table; every request is recorded in `sent`. */
function mockApi(routes: Record<string, unknown | (() => unknown)>) {
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

class FakeEventSource {
  static readonly CLOSED = 2
  static last: FakeEventSource | undefined
  readyState = 1
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  private listeners = new Map<string, ((message: MessageEvent<string>) => void)[]>()
  readonly url: string
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

let seq = 0
const node = (name: string, phase: 'start' | 'end', summary = ''): WorkflowEvent => ({
  seq: ++seq,
  thread_id: 'thread-1',
  type: 'node',
  node: name,
  phase,
  summary,
  duration_ms: phase === 'end' ? 840 : null,
})
const runEvent = (status: WorkflowEvent['status']): WorkflowEvent => ({
  seq: ++seq,
  thread_id: 'thread-1',
  type: 'run',
  status,
  summary: '',
})

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/plan/new" element={<NewPlanPage />} />
            <Route path="/plan/:threadId" element={<PlanRunPage />} />
            <Route path="/projects/:projectId" element={<p>Project page</p>} />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

const waiting = runState({ status: 'waiting', node: 'pm_review', review: REVIEW })

beforeEach(() => {
  seq = 0
  vi.stubGlobal('EventSource', FakeEventSource)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('NewPlanPage', () => {
  it('fills the demo brief, starts the run and opens it', async () => {
    const sent = mockApi({
      'GET /workflows/plan/example': EXAMPLE,
      'POST /workflows/plan': { thread_id: 'thread-1' },
      'GET /workflows/thread-1/state': runState({}),
    })
    renderAt('/plan/new')

    const generate = screen.getByRole('button', { name: 'Generate plan' })
    expect(generate.hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Use the demo brief' }))
    expect(await screen.findByDisplayValue('Campus Food-Ordering App v2')).toBeTruthy()
    expect((screen.getByLabelText('Deadline') as HTMLInputElement).value).toBe('2027-03-05')

    fireEvent.click(generate)
    expect(await screen.findByText('Planning run')).toBeTruthy()
    const start = sent.find((r) => r.method === 'POST')
    expect(start?.body).toMatchObject({
      project_name: 'Campus Food-Ordering App v2',
      brief: EXAMPLE.brief,
      deadline: '2027-03-05',
      start_date: '2026-11-16',
      budget: '900000',
    })
    expect(start?.headers['X-Actor']).toBe('PM')
  })
})

describe('PlanRunPage', () => {
  it('streams the timeline, then lets the PM edit and request changes', async () => {
    let state: WorkflowState = runState({ status: 'running', node: 'decompose' })
    const sent = mockApi({
      'GET /workflows/thread-1/state': () => state,
      'GET /skills?limit=200': SKILLS,
      'POST /workflows/thread-1/resume': { thread_id: 'thread-1', status: 'running' },
    })
    renderAt('/plan/thread-1')
    expect(await screen.findByText('Drafting and estimating the plan.')).toBeTruthy()
    expect(FakeEventSource.last?.url).toMatch(/\/workflows\/thread-1\/events$/)

    const stream = FakeEventSource.last!
    stream.emit(node('decompose', 'start'))
    stream.emit(node('decompose', 'end', '2 tasks in 1 epic'))
    stream.emit(node('pm_review', 'start'))
    stream.emit(node('pm_review', 'end', 'waiting for PM review'))
    state = waiting
    stream.emit(runEvent('waiting'))

    const steps = screen.getByRole('list', { name: 'Workflow steps' })
    expect(within(steps).getByText('Decompose brief')).toBeTruthy()
    expect(within(steps).getByText('2 tasks in 1 epic')).toBeTruthy()
    expect(within(steps).getByText('waiting for you')).toBeTruthy()

    // Review: engine numbers and the WBS.
    expect(await screen.findByText('Menu and cart API')).toBeTruthy()
    expect(screen.getByText('Diya Nair')).toBeTruthy()
    const approve = screen.getByRole('button', { name: 'Approve plan' })
    const requestChanges = screen.getByRole('button', { name: /Request changes/ })
    expect(approve.hasAttribute('disabled')).toBe(false)
    expect(requestChanges.hasAttribute('disabled')).toBe(true)

    // A broken estimate blocks sending; a valid one enables it and blocks approval.
    const m = screen.getByLabelText('T-001 m hours')
    fireEvent.change(m, { target: { value: '25' } })
    expect(screen.getByText(/Need 1 ≤ o ≤ m ≤ p ≤ 80 hours/)).toBeTruthy()
    expect(requestChanges.hasAttribute('disabled')).toBe(true)
    fireEvent.change(m, { target: { value: '14' } })
    expect(screen.queryByText(/Need 1 ≤ o ≤ m ≤ p/)).toBeNull()
    expect(approve.hasAttribute('disabled')).toBe(true)

    fireEvent.change(screen.getByLabelText('T-002 payments level'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Request changes (2)' }))

    await vi.waitFor(() => expect(sent.some((r) => r.method === 'POST')).toBe(true))
    const resume = sent.find((r) => r.method === 'POST')
    expect(resume?.body).toEqual({
      action: 'edit',
      changes: [
        { op: 'update', task_id: 'T-001', m: 14 },
        {
          op: 'update',
          task_id: 'T-002',
          required_skills: [{ skill: 'payments', level: 3, must: true }],
        },
      ],
    })
    expect(resume?.headers['X-Actor']).toBe('PM')
  })

  it('approves, and links to the created project once committed', async () => {
    let state: WorkflowState = waiting
    const sent = mockApi({
      'GET /workflows/thread-1/state': () => state,
      'GET /skills?limit=200': SKILLS,
      'POST /workflows/thread-1/resume': { thread_id: 'thread-1', status: 'running' },
    })
    renderAt('/plan/thread-1')

    fireEvent.click(await screen.findByRole('button', { name: 'Approve plan' }))
    await vi.waitFor(() => expect(sent.some((r) => r.method === 'POST')).toBe(true))
    expect(sent.find((r) => r.method === 'POST')?.body).toEqual({ action: 'approve' })

    state = runState({ status: 'committed', project_id: 7 })
    FakeEventSource.last!.emit(runEvent('committed'))
    expect(await screen.findByText('P-007')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Open overview' }).getAttribute('href')).toBe(
      '/projects/7',
    )
    expect(FakeEventSource.last!.readyState).toBe(FakeEventSource.CLOSED)
  })

  it('needs a reason to reject', async () => {
    const sent = mockApi({
      'GET /workflows/thread-1/state': waiting,
      'GET /skills?limit=200': SKILLS,
      'POST /workflows/thread-1/resume': { thread_id: 'thread-1', status: 'running' },
    })
    renderAt('/plan/thread-1')

    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }))
    const confirm = screen.getByRole('button', { name: 'Reject plan' })
    expect(confirm.hasAttribute('disabled')).toBe(true)
    fireEvent.change(screen.getByLabelText('Why reject this plan'), {
      target: { value: 'Scope moved to next term' },
    })
    fireEvent.click(confirm)
    await vi.waitFor(() =>
      expect(sent.find((r) => r.method === 'POST')?.body).toEqual({
        action: 'reject',
        reason: 'Scope moved to next term',
      }),
    )
  })

  it('shows not found for an unknown run', async () => {
    mockApi({})
    renderAt('/plan/nope')
    expect(await screen.findByRole('heading', { name: 'Planning run not found' })).toBeTruthy()
  })
})
