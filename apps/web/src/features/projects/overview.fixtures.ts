/** API responses for the overview smoke test: the plan.md demo numbers (P 81%, SPI 0.92, CPI 1.04). */
import type {
  MemberPage,
  Project,
  ProjectCpm,
  ProjectEvm,
  ProjectForecast,
  ProjectFull,
  ProjectSchedule,
  RiskPage,
  Task,
} from '@/lib/api/schemas'

const STAMP = '2026-11-06T09:00:00Z'

export const PROJECT: Project = {
  id: 1,
  name: 'Campus Food-Ordering App',
  brief: null,
  start_date: '2026-10-05',
  deadline: '2026-12-18',
  budget: '1500000.00',
  hourly_rate: '1250.00',
  sim_date: null,
  created_at: STAMP,
  updated_at: STAMP,
}

function task(id: number, title: string, status: Task['status']): Task {
  return {
    id,
    project_id: 1,
    epic_id: 1,
    title,
    description: null,
    optimistic_hours: 8,
    most_likely_hours: 16,
    pessimistic_hours: 30,
    priority: 2,
    status,
    required_skills: [],
    percent_complete: status === 'done' ? 100 : 0,
    actual_hours: 0,
    created_at: STAMP,
    updated_at: STAMP,
  }
}

export const FULL: ProjectFull = {
  project: PROJECT,
  epics: [],
  tasks: [
    task(11, 'Cart and checkout API', 'done'),
    task(12, 'Payment gateway integration', 'blocked'),
    task(13, 'Order tracking screen', 'todo'),
  ],
  dependencies: [],
  assignments: [
    {
      id: 1,
      task_id: 12,
      member_id: 1,
      score_breakdown: {},
      source: 'ai',
      reason: null,
      is_current: true,
      created_at: STAMP,
    },
  ],
}

export const MEMBERS: MemberPage = {
  items: [
    {
      id: 1,
      name: 'Aarav Mehta',
      role: 'Backend engineer',
      email: null,
      skills: [],
      availability: [],
      created_at: STAMP,
      updated_at: STAMP,
    },
  ],
  total: 1,
  limit: 200,
  offset: 0,
}

const percentile = (hours: number, on: string) => ({ hours, on })

export const FORECAST: ProjectForecast = {
  project_id: 1,
  as_of: '2026-11-06',
  runs: 5000,
  seed: 42,
  deadline: PROJECT.deadline,
  deadline_hours: 400,
  p_on_time: 0.81,
  mean_hours: 380,
  p50: percentile(378, '2026-12-14'),
  p80: percentile(398, '2026-12-17'),
  p95: percentile(415, '2026-12-21'),
  histogram: [],
  cdf: [],
  criticality: {},
  resource_shift_hours: 0,
}

export const EVM: ProjectEvm = {
  project_id: 1,
  as_of: '2026-11-06',
  budget: '1500000.00',
  bac: '1200000.00',
  pv: '500000.00',
  ev: '460000.00',
  ac: '442307.69',
  sv: '-40000.00',
  cv: '17692.31',
  spi: 0.92,
  cpi: 1.04,
  eac: '1153846.15',
  etc: '711538.46',
  vac: '46153.85',
  tcpi: 0.98,
  notes: {},
  snapshots: [
    { on: '2026-10-30', pv: '400000.00', ev: '380000.00', ac: '370000.00' },
    { on: '2026-11-06', pv: '500000.00', ev: '460000.00', ac: '442307.69' },
  ],
  planned: [],
}

const cpmRow = (taskId: number, critical: boolean) => ({
  task_id: taskId,
  duration_hours: 16.33,
  es: 0,
  ef: 16.33,
  ls: critical ? 0 : 8,
  lf: critical ? 16.33 : 24.33,
  total_slack: critical ? 0 : 8,
  free_slack: critical ? 0 : 8,
  critical,
})

export const CPM: ProjectCpm = {
  project_id: 1,
  project_duration_hours: 400,
  critical_paths: [[11, 12]],
  tasks: [cpmRow(11, true), cpmRow(12, true), cpmRow(13, false)],
}

export const SCHEDULE: ProjectSchedule = {
  project_id: 1,
  start: PROJECT.start_date,
  finish: '2026-12-16',
  deadline: PROJECT.deadline,
  tasks: [],
  loads: [
    { member_id: 1, week_start: '2026-11-09', hours: 44, capacity: 40, utilisation: 1.1 },
    { member_id: 2, week_start: '2026-11-09', hours: 32, capacity: 40, utilisation: 0.8 },
  ],
  delayed: [],
}

export const RISKS: RiskPage = {
  items: [
    {
      id: 1,
      project_id: 1,
      rule_key: 'bus_factor',
      subject_ref: 'task:12',
      title: 'T-012 Payment gateway integration: only Aarav Mehta can do this critical task',
      description: null,
      category: 'resource',
      probability: 4,
      impact: 4,
      status: 'open',
      evidence: {},
      rmmm: null,
      created_at: STAMP,
      updated_at: STAMP,
      score: 16,
    },
    {
      id: 2,
      project_id: 1,
      rule_key: 'member_overload',
      subject_ref: 'member:1',
      title: 'Aarav Mehta is over capacity in 1 week(s), peak 110%',
      description: null,
      category: 'resource',
      probability: 3,
      impact: 3,
      status: 'mitigating',
      evidence: {},
      rmmm: null,
      created_at: STAMP,
      updated_at: STAMP,
      score: 9,
    },
    {
      id: 3,
      project_id: 1,
      rule_key: 'spi_low',
      subject_ref: 'project',
      title: 'Schedule performance below 0.9',
      description: null,
      category: 'schedule',
      probability: 3,
      impact: 4,
      status: 'closed',
      evidence: {},
      rmmm: null,
      created_at: STAMP,
      updated_at: STAMP,
      score: 12,
    },
  ],
  total: 3,
  limit: 200,
  offset: 0,
}

/** Path (with query) -> response body for project 1. */
export const OVERVIEW_ROUTES: Record<string, unknown> = {
  '/projects/1/full': FULL,
  '/projects/1/forecast': FORECAST,
  '/projects/1/evm': EVM,
  '/projects/1/cpm': CPM,
  '/projects/1/schedule': SCHEDULE,
  '/projects/1/risks?limit=200': RISKS,
  '/members?limit=200': MEMBERS,
}
