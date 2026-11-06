/**
 * Mock data for "Campus Food-Ordering App", shaped like the Step 03 tables.
 * These names are provisional: replace with the Step 04 seed when the API serves it.
 */
import type {
  Assignment,
  Dependency,
  Epic,
  Member,
  Project,
  RequiredSkill,
  Skill,
  Task,
  TaskStatus,
} from '../provisional'

const PROJECT_START = '2026-10-19'
const PROJECT_END = '2026-12-18'

export const projects: Project[] = [
  {
    id: 1,
    name: 'Campus Food-Ordering App',
    brief:
      'Students order from campus canteens, pay online and track pickup. Vendors manage menus and a live order queue.',
    start_date: PROJECT_START,
    deadline: PROJECT_END,
    budget: '620000.00',
    hourly_rate: '850.00',
  },
  {
    id: 2,
    name: 'Library Seat Booking',
    brief: 'Students reserve reading-room seats by the hour and check in with a QR code.',
    start_date: '2027-01-11',
    deadline: '2027-03-05',
    budget: '280000.00',
    hourly_rate: '850.00',
  },
]

export const skills: Skill[] = [
  'react',
  'typescript',
  'nodejs',
  'python',
  'fastapi',
  'postgres',
  'mongodb',
  'docker',
  'devops',
  'testing',
  'ui-design',
  'android',
  'payments',
  'security',
].map((name, index) => ({ id: index + 1, name }))

const memberRows: [string, string, number, Record<string, number>][] = [
  ['Aarav Mehta', 'Backend lead', 40, { fastapi: 5, postgres: 4, python: 4, payments: 3, security: 3, docker: 2 }],
  ['Diya Nair', 'Full-stack engineer', 40, { fastapi: 4, postgres: 3, react: 3, typescript: 3 }],
  ['Kabir Singh', 'Backend engineer', 36, { nodejs: 4, fastapi: 3, python: 3, mongodb: 3 }],
  ['Meera Iyer', 'Frontend lead', 40, { react: 5, typescript: 4, 'ui-design': 3 }],
  ['Rohan Gupta', 'Frontend engineer', 32, { 'ui-design': 4, react: 3, typescript: 3, android: 2 }],
  ['Sneha Kulkarni', 'QA engineer', 30, { testing: 5, python: 3, typescript: 2, security: 2 }],
  ['Arjun Rao', 'DevOps engineer', 36, { docker: 5, devops: 5, postgres: 3, security: 3 }],
  ['Ishita Sharma', 'Android engineer (part-time)', 20, { android: 4, react: 2, payments: 2 }],
]

export const members: Member[] = memberRows.map(([name, role, hours, levels], index) => ({
  id: index + 1,
  name,
  role,
  email: `${name.split(' ')[0].toLowerCase()}@orchestrai.test`,
  skills: Object.entries(levels).map(([skill, level]) => ({ skill, level })),
  availability: [
    {
      kind: 'work',
      start_date: PROJECT_START,
      end_date: PROJECT_END,
      hours_per_week: hours,
      note: null,
    },
  ],
}))

export const epics: Epic[] = [
  'Auth',
  'Menu & Catalogue',
  'Ordering & Payments',
  'Vendor Dashboard',
  'Release',
].map((title, index) => ({
  id: index + 1,
  project_id: 1,
  title,
  description: null,
  position: index,
}))

/** "react:3!" means react level 3, must-have. */
function parseSkills(spec: string): RequiredSkill[] {
  return spec.split(',').map((part) => {
    const [skill, level] = part.replace('!', '').split(':')
    return { skill, level: Number(level), must: part.endsWith('!') }
  })
}

type TaskRow = [
  epic: number,
  title: string,
  o: number,
  m: number,
  p: number,
  priority: number,
  status: TaskStatus,
  percent: number,
  actual: number,
  skills: string,
]

const taskRows: TaskRow[] = [
  [1, 'Define auth flows and session model', 4, 6, 10, 2, 'done', 100, 7, 'security:3!,fastapi:2'],
  [1, 'Student sign-up with campus email OTP', 8, 14, 22, 1, 'done', 100, 16, 'fastapi:3!,postgres:2'],
  [1, 'Role-based access for vendors and admins', 6, 10, 16, 2, 'done', 100, 11, 'fastapi:3!,security:3'],
  [1, 'Login and profile screens', 8, 12, 20, 2, 'done', 100, 13, 'react:3!,typescript:2'],
  [2, 'Menu and catalogue schema', 6, 10, 14, 1, 'done', 100, 12, 'postgres:3!,fastapi:2'],
  [2, 'Catalogue CRUD API', 10, 16, 26, 1, 'done', 100, 18, 'fastapi:3!'],
  [2, 'Menu image upload and storage', 6, 10, 18, 3, 'in_progress', 70, 8, 'fastapi:2!,devops:2'],
  [2, 'Search and dietary filters', 8, 14, 24, 3, 'in_progress', 45, 7, 'postgres:3!,fastapi:3'],
  [2, 'Menu browsing screens', 12, 18, 30, 2, 'in_progress', 60, 12, 'react:3!,ui-design:2'],
  [3, 'Order state machine', 8, 12, 20, 1, 'done', 100, 14, 'fastapi:4!,postgres:3'],
  [3, 'Cart and checkout API', 12, 20, 32, 1, 'in_progress', 40, 10, 'fastapi:4!'],
  [3, 'Payment gateway integration', 16, 24, 40, 1, 'blocked', 0, 0, 'payments:4!,security:3'],
  [3, 'Payment webhooks and retries', 8, 14, 24, 1, 'todo', 0, 0, 'payments:3!,fastapi:3'],
  [3, 'Cart and checkout screens', 12, 20, 30, 1, 'todo', 0, 0, 'react:3!,typescript:3'],
  [3, 'Live order tracking', 14, 22, 36, 2, 'todo', 0, 0, 'fastapi:3!,react:3'],
  [3, 'Android wrapper for students', 10, 18, 34, 3, 'todo', 0, 0, 'android:3!'],
  [4, 'Vendor order queue API', 8, 14, 22, 2, 'todo', 0, 0, 'fastapi:3!'],
  [4, 'Vendor dashboard screens', 14, 22, 34, 2, 'todo', 0, 0, 'react:3!,ui-design:3'],
  [4, 'Daily sales report', 6, 10, 16, 4, 'todo', 0, 0, 'postgres:2!,react:2'],
  [4, 'Stock and availability toggles', 4, 8, 14, 3, 'todo', 0, 0, 'fastapi:2!,react:2'],
  [5, 'End-to-end test suite', 12, 18, 28, 2, 'todo', 0, 0, 'testing:3!'],
  [5, 'Load test at lunch peak', 6, 10, 18, 3, 'todo', 0, 0, 'testing:3!,devops:2'],
  [5, 'Security review', 6, 10, 16, 2, 'todo', 0, 0, 'security:4!'],
  [5, 'CI/CD and staging', 8, 12, 20, 2, 'in_progress', 30, 4, 'docker:3!,devops:3'],
  [5, 'Production rollout', 4, 8, 14, 1, 'todo', 0, 0, 'devops:3!,docker:3'],
]

export const tasks: Task[] = taskRows.map(
  ([epic_id, title, o, m, p, priority, status, percent, actual, spec], index) => ({
    id: index + 1,
    project_id: 1,
    epic_id,
    title,
    description: null,
    optimistic_hours: o,
    most_likely_hours: m,
    pessimistic_hours: p,
    priority,
    status,
    required_skills: parseSkills(spec),
    percent_complete: percent,
    actual_hours: actual,
  }),
)

const dependencyRows: [number, number][] = [
  [1, 2], [1, 3], [2, 4], [5, 6], [6, 7], [6, 8], [6, 9], [2, 10], [5, 10], [10, 11],
  [11, 12], [12, 13], [11, 14], [13, 15], [14, 15], [14, 16], [10, 17], [17, 18], [17, 19],
  [6, 20], [15, 21], [18, 21], [16, 21], [21, 22], [21, 23], [24, 25], [22, 25], [23, 25],
]

export const dependencies: Dependency[] = dependencyRows.map(([pred, succ], index) => ({
  id: index + 1,
  pred_task_id: pred,
  succ_task_id: succ,
  type: 'FS',
}))

/** Started tasks only: [task, member, skill_fit, capacity_fit, balance]. */
const assignmentRows: [number, number, number, number, number][] = [
  [1, 1, 1, 0.9, 0.6], [2, 2, 1, 0.85, 0.7], [3, 1, 1, 0.8, 0.5], [4, 4, 1, 0.95, 0.8],
  [5, 2, 1, 0.9, 0.65], [6, 1, 1, 0.75, 0.45], [7, 7, 1, 0.8, 0.75], [8, 2, 1, 0.7, 0.55],
  [9, 5, 1, 0.85, 0.7], [10, 1, 1, 0.7, 0.4], [11, 1, 1, 0.65, 0.35], [24, 7, 1, 0.9, 0.7],
]

export const assignments: Assignment[] = assignmentRows.map(
  ([task_id, member_id, skill_fit, capacity_fit, balance], index) => ({
    id: index + 1,
    task_id,
    member_id,
    score_breakdown: {
      score: Math.round(1000 * (0.6 * skill_fit + 0.25 * capacity_fit + 0.15 * balance)) / 10,
      skill_fit,
      capacity_fit,
      balance,
    },
    source: 'ai',
    reason: null,
    is_current: true,
    created_at: '2026-10-19T04:30:00Z',
  }),
)
