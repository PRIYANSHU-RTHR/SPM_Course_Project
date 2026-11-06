/**
 * Provisional response types, mirroring the Step 03 models and the Step 05 brief.
 * Delete this file after Step 05 merges: run `pnpm gen:api` and import from types.ts instead.
 */

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Project {
  id: number
  name: string
  brief: string | null
  start_date: string
  deadline: string
  /** Decimal, serialised as a string. */
  budget: string
  hourly_rate: string
}

export interface Epic {
  id: number
  project_id: number
  title: string
  description: string | null
  position: number
}

export interface RequiredSkill {
  skill: string
  level: number
  must: boolean
}

export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'done'

export interface Task {
  id: number
  project_id: number
  epic_id: number
  title: string
  description: string | null
  optimistic_hours: number
  most_likely_hours: number
  pessimistic_hours: number
  priority: number
  status: TaskStatus
  required_skills: RequiredSkill[]
  /** 0–100, as stored in the task table. */
  percent_complete: number
  actual_hours: number
}

export interface Dependency {
  id: number
  pred_task_id: number
  succ_task_id: number
  type: 'FS'
}

export interface ScoreBreakdown {
  score: number
  skill_fit: number
  capacity_fit: number
  balance: number
}

export interface Assignment {
  id: number
  task_id: number
  member_id: number
  score_breakdown: ScoreBreakdown
  source: 'ai' | 'pm_override'
  reason: string | null
  is_current: boolean
  created_at: string
}

export interface MemberSkill {
  skill: string
  level: number
}

export interface Availability {
  kind: 'work' | 'leave'
  start_date: string
  end_date: string
  hours_per_week: number
  note: string | null
}

export interface Member {
  id: number
  name: string
  role: string
  email: string | null
  skills: MemberSkill[]
  availability: Availability[]
}

export interface Skill {
  id: number
  name: string
}

export interface ProjectFull extends Project {
  epics: Epic[]
  tasks: Task[]
  dependencies: Dependency[]
  assignments: Assignment[]
}
