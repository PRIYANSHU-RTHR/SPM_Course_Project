/** API responses for the approvals and audit tests (project 1 from the overview fixtures). */
import { PROJECT } from '@/features/projects/overview.fixtures'
import type {
  AuditPage,
  ProjectMetrics,
  ProjectPage,
  Proposal,
  ProposalPage,
} from '@/lib/api/schemas'

export const PROJECTS: ProjectPage = { items: [PROJECT], total: 1, limit: 100, offset: 0 }

export const METRICS: ProjectMetrics = {
  project_id: 1,
  as_of: '2026-11-06',
  deadline: PROJECT.deadline,
  p_on_time: 0.3,
  p50: '2026-12-15',
  p80: '2026-12-21',
  spi: 0.94,
  cpi: 1.05,
  open_risks: 4,
  overloaded_members: 1,
}

const scenario = (p: number, finish: string) => ({
  p_on_time: p,
  p50: finish,
  p80: finish,
  p80_hours: 400,
  finish,
  resource_shift_hours: 0,
})

export const PENDING: Proposal = {
  id: 3,
  project_id: 1,
  thread_id: 'realloc-abc',
  disruption: { type: 'leave', member_id: 1, start_date: '2026-11-09', end_date: '2026-11-20' },
  status: 'pending',
  decided_by: null,
  reason: null,
  created_at: '2026-11-06T09:00:00Z',
  decided_at: null,
  payload: {
    reallocation_id: 3,
    thread_id: 'realloc-abc',
    project_id: 1,
    as_of: '2026-11-06',
    disruption: {},
    summary: 'Moving 1 task brings P(on time) from 0% to 11%.',
    before_disruption: scenario(0.3, '2026-12-09'),
    now: scenario(0, '2026-12-23'),
    if_approved: scenario(0.11, '2026-12-10'),
    items: [
      {
        task_id: 12,
        title: 'Payment gateway integration',
        reasons: ['owner_unavailable'],
        before: { member_id: 1, name: 'Aarav Mehta' },
        after: { member_id: 4, name: 'Diya Nair' },
        changed: true,
        before_eligible: false,
        before_ineligible_reason: 'on leave 09 Nov – 20 Nov',
        score_before: 40,
        score_after: 82,
        finish_before: '2026-11-27',
        finish_after: '2026-11-20',
      },
    ],
    risks_that_would_close: [
      {
        risk_id: 1,
        rule_key: 'bus_factor',
        subject_ref: 'task:12',
        title: 'Only Aarav can do T-012',
        score: 16,
      },
    ],
    risks_that_would_open: [],
  },
}

export const DECIDED: Proposal = {
  ...PENDING,
  id: 2,
  thread_id: 'realloc-old',
  disruption: { type: 'slip', task_id: 12, extra_hours: 16 },
  status: 'rejected',
  decided_by: 'pm:asha',
  reason: 'Back early',
  decided_at: '2026-11-05T10:00:00Z',
  payload: null,
}

export const PROPOSALS: ProposalPage = { items: [PENDING, DECIDED], total: 2, limit: 20, offset: 0 }

const entry = (id: number, at: string, summary: string, actor = 'PM') => ({
  id,
  actor,
  action: 'disruption.leave',
  entity: 'project',
  entity_id: 1,
  before: null,
  after: null,
  reason: id === 5 ? 'Family emergency' : null,
  created_at: at,
  summary,
})

export const AUDIT_FIRST: AuditPage = {
  items: [
    entry(
      5,
      '2026-11-10T09:24:00Z',
      'PM recorded leave for Aarav Mehta from 2026-11-09 to 2026-11-20',
    ),
    entry(
      4,
      '2026-11-09T16:00:00Z',
      'Risk engine opened risk “Only Aarav can do T-012” (P4 x I4 = 16)',
      'system:risk-engine',
    ),
  ],
  total: 3,
  limit: 30,
  offset: 0,
}

export const AUDIT_SECOND: AuditPage = {
  items: [
    entry(
      3,
      '2026-11-08T12:00:00Z',
      'PM advanced the simulated clock from 2026-11-01 to 2026-11-08 (5 working days)',
    ),
  ],
  total: 3,
  limit: 30,
  offset: 2,
}
