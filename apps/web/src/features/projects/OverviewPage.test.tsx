// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { FULL, OVERVIEW_ROUTES } from './overview.fixtures'
import { OverviewPage } from './OverviewPage'

const NOT_FOUND = { error: { code: 'not_found', message: 'Project 9 not found', details: {} } }

/** Answers `fetch` from a path -> body table; anything else is the API's 404 body. */
function mockApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(input instanceof Request ? input.url : String(input))
    const body = routes[url.pathname + url.search]
    return body === undefined
      ? new Response(JSON.stringify(NOT_FOUND), { status: 404 })
      : new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderOverview(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/projects/:projectId" element={<OverviewPage />} />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

/** The value shown under a KPI label. */
async function kpi(label: string) {
  const name = await screen.findByText(label)
  const card = name.closest('div')?.parentElement
  if (!card) throw new Error(`no KPI card for ${label}`)
  return card.textContent ?? ''
}

beforeEach(() => {
  // Recharts measures its container; jsdom has no layout.
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

describe('OverviewPage', () => {
  it('shows the project, its KPIs, top risks and the next critical tasks', async () => {
    mockApi(OVERVIEW_ROUTES)
    renderOverview('/projects/1')

    expect(await screen.findByRole('heading', { name: 'Campus Food-Ordering App' })).toBeTruthy()
    expect(screen.getByText('P-001')).toBeTruthy()

    expect(await kpi('P(on time)')).toContain('81%')
    expect(await kpi('SPI')).toContain('0.92')
    expect(await kpi('CPI')).toContain('1.04')
    expect(await kpi('Critical tasks')).toContain('2')
    expect(await kpi('Overloaded')).toContain('1')
    expect(await kpi('Open risks')).toContain('2') // `closed` is not counted

    // Highest score first; the closed risk is not listed.
    const risks = await screen.findByText(/only Aarav Mehta can do this critical task/)
    expect(risks).toBeTruthy()
    expect(screen.queryByText('Schedule performance below 0.9')).toBeNull()

    // Done tasks drop off the critical list: T-011 is done, T-012 is next.
    const row = (await screen.findByText('T-012')).closest('tr')
    expect(row).not.toBeNull()
    expect(within(row as HTMLElement).getByText('Payment gateway integration')).toBeTruthy()
    expect(screen.queryByText('T-011')).toBeNull()

    expect(screen.getByRole('img', { name: /S-curve to 2026-11-06/ })).toBeTruthy()
  })

  it('shows the empty state for a project without tasks', async () => {
    mockApi({ ...OVERVIEW_ROUTES, '/projects/1/full': { ...FULL, tasks: [], assignments: [] } })
    renderOverview('/projects/1')

    expect(await screen.findByText('This project has no tasks yet.')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Plan this project' }).getAttribute('href')).toBe(
      '/plan/new',
    )
  })

  it('shows not found for an unknown project', async () => {
    mockApi(OVERVIEW_ROUTES)
    renderOverview('/projects/9')

    expect(await screen.findByRole('heading', { name: 'Project not found' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'All projects' })).toBeTruthy()
  })

  it('shows an error with a retry when the API fails', async () => {
    const fetchMock = mockApi(OVERVIEW_ROUTES)
    fetchMock.mockImplementation(async () => new Response('oops', { status: 500 }))
    renderOverview('/projects/1')

    expect(await screen.findByText('Request failed with status 500')).toBeTruthy()

    // Retry refetches; once the API is back the page renders.
    mockApi(OVERVIEW_ROUTES)
    act(() => screen.getByRole('button', { name: 'Try again' }).click())
    expect(await screen.findByRole('heading', { name: 'Campus Food-Ordering App' })).toBeTruthy()
  })
})
