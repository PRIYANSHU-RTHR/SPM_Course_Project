/** Geometry for the Gantt chart. All positions are pixels from the first day on the axis. */
import { addDays, addWorkingDays, daysBetween, isMonday, isWeekend, slackDays } from '@/lib/dates'
import type { Plan, PlanTask } from './plan'

export type Zoom = 'day' | 'week'

export const DAY_WIDTH: Record<Zoom, number> = { day: 28, week: 11 }
export const ROW_HEIGHT = 32
const END_PADDING_DAYS = 4

export interface Timeline {
  first: string
  days: string[]
  mondays: string[]
  weekends: string[]
}

export function buildTimeline(plan: Plan, today: string): Timeline {
  const ends = plan.tasks.map((task) => slackEnd(task))
  const last = [plan.finish, plan.deadline, today, ...ends].reduce((a, b) => (a > b ? a : b))
  const first = plan.start < today ? plan.start : today
  const count = daysBetween(first, last) + END_PADDING_DAYS
  const days = Array.from({ length: count }, (_, index) => addDays(first, index))
  return {
    first,
    days,
    mondays: days.filter(isMonday),
    weekends: days.filter(isWeekend),
  }
}

/** Last day of the task's slack, or its own end when it has none. */
export function slackEnd(task: PlanTask): string {
  return addWorkingDays(task.end, slackDays(task.totalSlack))
}

export function dayX(timeline: Timeline, date: string, zoom: Zoom): number {
  return daysBetween(timeline.first, date) * DAY_WIDTH[zoom]
}

/** Horizontal span of a task bar. A task covers its whole end day. */
export function barSpan(timeline: Timeline, task: PlanTask, zoom: Zoom) {
  const left = dayX(timeline, task.start, zoom)
  const right = dayX(timeline, addDays(task.end, 1), zoom)
  const tailEnd = dayX(timeline, addDays(slackEnd(task), 1), zoom)
  return { left, width: right - left, tail: tailEnd - right }
}

export type GanttRow =
  | { kind: 'epic'; key: string; title: string }
  | { kind: 'task'; key: string; task: PlanTask }

export function buildRows(plan: Plan): GanttRow[] {
  return plan.epics.flatMap(({ epic, tasks }) => [
    { kind: 'epic' as const, key: `epic-${epic.id}`, title: epic.title },
    ...tasks.map((task) => ({ kind: 'task' as const, key: `task-${task.id}`, task })),
  ])
}

/** Elbow path from the end of `pred` to the start of `succ`. Rows are indexes into the row list. */
export function dependencyPath(
  from: { x: number; row: number },
  to: { x: number; row: number },
): string {
  const y1 = from.row * ROW_HEIGHT + ROW_HEIGHT / 2
  const y2 = to.row * ROW_HEIGHT + ROW_HEIGHT / 2
  const bend = Math.max(from.x + 6, to.x - 6)
  return `M ${from.x} ${y1} H ${bend} V ${y2} H ${to.x}`
}
