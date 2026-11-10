/** A small PM-review payload and skill list for the plan flow tests. */
import type { PlanExample, PlanReview, SkillPage, WorkflowState } from '@/lib/api/schemas'

const STAMP = '2026-11-06T09:00:00Z'
const score = (total: number) => ({
  total,
  skill_fit: 1,
  capacity_fit: 1,
  balance: 1,
  skill_part: total * 0.6,
  capacity_part: total * 0.25,
  balance_part: total * 0.15,
  free_hours: 40,
  utilisation: 0.3,
  skills: [],
})

export const REVIEW: PlanReview = {
  thread_id: 'thread-1',
  revision: 0,
  project_name: 'Campus Food-Ordering App v2',
  wbs: {
    epics: [
      {
        local_id: 'E-1',
        title: 'Ordering & Payments',
        tasks: [
          {
            local_id: 'T-001',
            title: 'Menu and cart API',
            description: '',
            required_skills: [{ skill: 'python', level: 3, must: true }],
            o: 8,
            m: 12,
            p: 20,
            predecessors: [],
          },
          {
            local_id: 'T-002',
            title: 'UPI payment flow',
            description: '',
            required_skills: [{ skill: 'payments', level: 4, must: true }],
            o: 12,
            m: 16,
            p: 30,
            predecessors: ['T-001'],
          },
        ],
      },
    ],
    assumptions: ['Campus SSO is available'],
  },
  warnings: [],
  estimates: {
    total_te_hours: 30.67,
    total_std_hours: 3.4,
    total_effort_pm: 0.2,
    estimated_cost: '38333.33',
    budget: '900000.00',
    cocomo: null,
    tasks: [
      { task_id: 'T-001', te_hours: 12.67, std_hours: 2 },
      { task_id: 'T-002', te_hours: 18, std_hours: 3 },
    ],
  },
  schedule: {
    start: '2026-11-16',
    finish: '2026-11-20',
    deadline: '2027-03-05',
    duration_hours: 30.67,
    meets_deadline: true,
    critical_path: ['T-001', 'T-002'],
    tasks: [
      { task_id: 'T-001', start: '2026-11-16', end: '2026-11-17', total_slack_hours: 0, critical: true },
      { task_id: 'T-002', start: '2026-11-18', end: '2026-11-20', total_slack_hours: 0, critical: true },
    ],
  },
  recommendations: {
    mode: 'optimal',
    total_score: 182,
    utilisation_std: 0.1,
    unassigned: 0,
    finish_with_owners: '2026-11-20',
    items: [
      {
        task_id: 'T-001',
        member_id: 2,
        member_name: 'Diya Nair',
        score: score(91),
        candidates: [],
        ineligible_count: 0,
      },
      {
        task_id: 'T-002',
        member_id: 1,
        member_name: 'Aarav Mehta',
        score: score(91),
        candidates: [],
        ineligible_count: 1,
      },
    ],
  },
}

export function runState(overrides: Partial<WorkflowState>): WorkflowState {
  return {
    kind: 'plan',
    thread_id: 'thread-1',
    status: 'running',
    node: null,
    revision: 0,
    review: null,
    project_id: null,
    reason: null,
    error: null,
    ...overrides,
  }
}

export const SKILLS: SkillPage = {
  items: ['python', 'payments', 'react'].map((name, i) => ({
    id: i + 1,
    name,
    created_at: STAMP,
    updated_at: STAMP,
  })),
  total: 3,
  limit: 200,
  offset: 0,
}

export const EXAMPLE: PlanExample = {
  brief: '# Campus Food-Ordering App\n\nStudents order from campus canteens and pay by UPI.',
  project_name: 'Campus Food-Ordering App v2',
  start_date: '2026-11-16',
  deadline: '2027-03-05',
  budget: '900000.00',
  hourly_rate: '1250.00',
}
