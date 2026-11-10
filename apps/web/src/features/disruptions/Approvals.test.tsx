// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { FULL, MEMBERS } from '@/features/projects/overview.fixtures'
import { FakeEventSource, mockApi, type Routes as ApiRoutes } from '@/test/api'
import { ApprovalsPage } from './ApprovalsPage'
import { AuditPage } from './AuditPage'
import {
  AUDIT_FIRST,
  AUDIT_SECOND,
  METRICS,
  PENDING,
  PROJECTS,
  PROPOSALS,
} from './disruptions.fixtures'

const BASE: ApiRoutes = {
  'GET /projects?limit=100': PROJECTS,
  'GET /projects/1/metrics': METRICS,
  'GET /projects/1/proposals?limit=20': PROPOSALS,
  'GET /projects/1/full': FULL,
  'GET /members?limit=200': MEMBERS,
  'POST /workflows/realloc-abc/resume': { thread_id: 'realloc-abc', status: 'running' },
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/audit" element={<AuditPage />} />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  )
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ApprovalsPage', () => {
  it('shows metrics, the pending proposal diff, and approves it', async () => {
    const sent = mockApi(BASE)
    renderAt('/approvals')

    const card = (await screen.findByText('Aarav Mehta on leave 09 Nov – 20 Nov')).closest(
      'section',
    )!
    // P(on time) 30%: the KPI strip and the proposal's "before disruption" column.
    expect(screen.getAllByText('30%')).toHaveLength(2)
    expect(within(card).getByText('0%')).toBeTruthy() // now
    expect(within(card).getByText(PENDING.payload!.summary)).toBeTruthy()
    expect(within(card).getByText('+11 pts')).toBeTruthy()
    expect(within(card).getByText('Diya Nair')).toBeTruthy()
    expect(within(card).getByText('owner away')).toBeTruthy()
    expect(within(card).getByText('Only Aarav can do T-012')).toBeTruthy()
    expect(within(card).queryByText(/Approving finishes later/)).toBeNull() // Dec 10 < Dec 23
    // History: the rejected slip, with who and why.
    expect(screen.getByText('T-012 Payment gateway integration needs 16 h more')).toBeTruthy()
    expect(screen.getByText('“Back early”')).toBeTruthy()

    fireEvent.click(within(card).getByRole('button', { name: 'Approve 1 reassignment' }))
    await vi.waitFor(() => expect(sent.some((r) => r.method === 'POST')).toBe(true))
    const decision = sent.find((r) => r.method === 'POST')!
    expect(decision.path).toBe('/workflows/realloc-abc/resume')
    expect(decision.body).toEqual({ action: 'approve' })
    expect(decision.headers['X-Actor']).toBe('PM')
  })

  it('records a leave and follows the reallocation run', async () => {
    const sent = mockApi({
      ...BASE,
      'GET /projects/1/proposals?limit=20': { ...PROPOSALS, items: [], total: 0 },
      'POST /projects/1/disruptions': { thread_id: 'realloc-new', project_id: 1 },
    })
    renderAt('/approvals')

    expect(await screen.findByText(/Nothing is waiting/)).toBeTruthy()
    fireEvent.change(await screen.findByLabelText('Member'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Record leave' }))

    await vi.waitFor(() => expect(FakeEventSource.last?.url).toMatch(/realloc-new\/events$/))
    expect(sent.find((r) => r.method === 'POST')?.body).toEqual({
      type: 'leave',
      member_id: 1,
      start_date: '2026-11-07',
      end_date: '2026-11-13',
      reason: null,
    })
    const stream = FakeEventSource.last!
    stream.emit({ seq: 1, thread_id: 'realloc-new', type: 'run', status: 'running', summary: '' })
    stream.emit({
      seq: 2,
      thread_id: 'realloc-new',
      type: 'node',
      node: 'apply_event',
      phase: 'start',
      summary: '',
    })
    stream.emit({
      seq: 3,
      thread_id: 'realloc-new',
      type: 'node',
      node: 'apply_event',
      phase: 'end',
      duration_ms: 31,
      summary: 'leave recorded; 1 open task affected',
    })
    expect(screen.getByText('Record disruption')).toBeTruthy()
    expect(screen.getByText('leave recorded; 1 open task affected')).toBeTruthy()
    expect(screen.getByText('The engines are computing a proposal.')).toBeTruthy()
  })
  it('warns when approving would finish later than doing nothing', async () => {
    const later = {
      ...PENDING,
      payload: {
        ...PENDING.payload!,
        if_approved: { ...PENDING.payload!.if_approved, finish: '2026-12-25' },
      },
    }
    mockApi({ ...BASE, 'GET /projects/1/proposals?limit=20': { ...PROPOSALS, items: [later] } })
    renderAt('/approvals')

    expect(await screen.findByText(/Approving finishes later \(25 Dec\)/)).toBeTruthy()
  })
})

describe('AuditPage', () => {
  it('groups entries by day and loads older ones', async () => {
    const sent = mockApi({
      'GET /projects?limit=100': PROJECTS,
      'GET /projects/1/audit?limit=30&offset=0': AUDIT_FIRST,
      'GET /projects/1/audit?limit=30&offset=2': AUDIT_SECOND,
    })
    renderAt('/audit')

    expect(await screen.findByText(/PM recorded leave for Aarav Mehta/)).toBeTruthy()
    expect(screen.getByText('“Family emergency”')).toBeTruthy()
    expect(screen.getByRole('region', { name: '10 Nov 2026' })).toBeTruthy()
    expect(screen.getByRole('region', { name: '09 Nov 2026' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Load older (1 more)' }))
    expect(await screen.findByText(/advanced the simulated clock/)).toBeTruthy()
    expect(sent.map((r) => r.path)).toContain('/projects/1/audit?limit=30&offset=2')
    expect(screen.queryByRole('button', { name: /Load older/ })).toBeNull()
  })
})
