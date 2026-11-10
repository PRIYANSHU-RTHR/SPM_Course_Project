/** Pure helpers for the brief-to-plan flow: SSE events -> timeline rows, PM edits -> changes. */
import type {
  PlannedTask,
  PlanReview,
  SkillReq,
  TaskChange,
  WorkflowEvent,
  WorkflowStatus,
} from '@/lib/api/schemas'

/** Graph nodes of `app/workflows/plan.py`, in run order. */
export const NODE_LABELS: Record<string, string> = {
  decompose: 'Decompose brief',
  validate: 'Validate WBS',
  estimate: 'Estimate',
  schedule: 'Schedule',
  recommend: 'Assign owners',
  pm_review: 'PM review',
  commit: 'Create project',
}

export const TERMINAL: ReadonlySet<WorkflowStatus> = new Set(['committed', 'rejected', 'failed'])

export type StepState = 'running' | 'done' | 'waiting' | 'failed'

export interface TimelineStep {
  /** Unique per occurrence: nodes run again after an edit. */
  key: string
  node: string
  label: string
  state: StepState
  durationMs: number | null
  summary: string
}

const WAITING_SUMMARY = /^waiting/

/** Merge new SSE events into the list: drop repeats (a reconnect replays history), keep seq order. */
export function mergeEvents(known: WorkflowEvent[], incoming: WorkflowEvent[]): WorkflowEvent[] {
  const bySeq = new Map(known.map((event) => [event.seq, event]))
  for (const event of incoming) bySeq.set(event.seq, event)
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq)
}

/** One row per node run: `start` opens it, the matching `end` closes it. */
export function buildTimeline(events: WorkflowEvent[]): TimelineStep[] {
  const steps: TimelineStep[] = []
  for (const event of events) {
    if (event.type === 'run') {
      if (event.status === 'failed') {
        for (const step of steps) if (step.state === 'running') step.state = 'failed'
      }
      continue
    }
    const node = event.node ?? 'unknown'
    if (event.phase === 'start') {
      steps.push({
        key: `${node}-${event.seq}`,
        node,
        label: NODE_LABELS[node] ?? node,
        state: 'running',
        durationMs: null,
        summary: '',
      })
    } else if (event.phase === 'end') {
      const open = steps.findLast((step) => step.node === node && step.state === 'running')
      if (!open) continue
      open.state = WAITING_SUMMARY.test(event.summary) ? 'waiting' : 'done'
      open.durationMs = event.duration_ms ?? null
      open.summary = event.summary
    }
  }
  return steps
}

/** Latest run status seen on the stream, if any. */
export function lastStatus(events: WorkflowEvent[]): WorkflowStatus | undefined {
  return events.findLast((event) => event.type === 'run')?.status ?? undefined
}

// -- PM edits -------------------------------------------------------------------------------

export interface TaskEdit {
  o?: number
  m?: number
  p?: number
  required_skills?: SkillReq[]
}

export type Edits = Record<string, TaskEdit>

export const MIN_HOURS = 1
export const MAX_HOURS = 80

/** Same rule the API enforces on edits: 1 <= o <= m <= p <= 80 hours. */
export function estimateError(o: number, m: number, p: number): string | null {
  if (![o, m, p].every(Number.isFinite)) return 'Enter hours for o, m and p.'
  if (!(MIN_HOURS <= o && o <= m && m <= p && p <= MAX_HOURS)) {
    return `Need ${MIN_HOURS} ≤ o ≤ m ≤ p ≤ ${MAX_HOURS} hours.`
  }
  return null
}

export function allTasks(review: PlanReview): PlannedTask[] {
  return review.wbs.epics.flatMap((epic) => epic.tasks)
}

/** The task with the PM's unsent edits applied. */
export function editedTask(task: PlannedTask, edit: TaskEdit | undefined): PlannedTask {
  return edit ? { ...task, ...edit } : task
}

function sameSkills(a: SkillReq[], b: SkillReq[]): boolean {
  const key = (list: SkillReq[]) =>
    list
      .map((s) => `${s.skill}:${s.level}:${s.must ?? true}`)
      .sort()
      .join('|')
  return key(a) === key(b)
}

/** Only real differences become `update` changes, in WBS order. */
export function toChanges(review: PlanReview, edits: Edits): TaskChange[] {
  const changes: TaskChange[] = []
  for (const task of allTasks(review)) {
    const edit = edits[task.local_id]
    if (!edit) continue
    const change: TaskChange = { op: 'update', task_id: task.local_id }
    if (edit.o !== undefined && edit.o !== task.o) change.o = edit.o
    if (edit.m !== undefined && edit.m !== task.m) change.m = edit.m
    if (edit.p !== undefined && edit.p !== task.p) change.p = edit.p
    const skills = edit.required_skills
    if (skills && !sameSkills(skills, task.required_skills ?? [])) change.required_skills = skills
    if (Object.keys(change).length > 2) changes.push(change)
  }
  return changes
}

/** Task ids whose edited hours break the rule; their changes can't be sent. */
export function invalidTasks(review: PlanReview, edits: Edits): string[] {
  return allTasks(review)
    .filter((task) => {
      const t = editedTask(task, edits[task.local_id])
      return edits[task.local_id] !== undefined && estimateError(t.o, t.m, t.p) !== null
    })
    .map((task) => task.local_id)
}
