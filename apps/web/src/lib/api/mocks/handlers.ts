import { bypass, http, HttpResponse, type RequestHandler } from 'msw'
import { API_URL } from '../client'
import type { RiskPage } from '../schemas'

/**
 * Mocks for endpoints the API does not have yet. Step 20 adds the workflow stream here.
 * Remove the plan handler once Step 16 is merged.
 */
export const handlers: RequestHandler[] = [
  http.post(`${API_URL}/projects/:projectId/risks/:riskId/plan`, async ({ params }) => {
    const list = `${API_URL}/projects/${String(params.projectId)}/risks?limit=200`
    const response = await fetch(bypass(list))
    const page = (await response.json()) as RiskPage
    const risk = page.items.find((item) => String(item.id) === params.riskId)
    if (!risk) {
      return HttpResponse.json(
        { error: { code: 'not_found', message: 'Risk not found', details: {} } },
        { status: 404 },
      )
    }
    return HttpResponse.json({
      ...risk,
      rmmm: {
        mitigation: 'Pair a second member with the current owner and write down the key steps.',
        monitoring_trigger: 'The task slips by one working day or its owner is unavailable.',
        contingency: 'Reassign the task and move non-critical work out of its way.',
        owner_role: 'Project manager',
        grounded: true,
        source: 'template',
        ungrounded: [],
      },
    })
  }),
]
