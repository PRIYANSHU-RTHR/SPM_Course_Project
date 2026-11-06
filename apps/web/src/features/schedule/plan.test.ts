import { describe, expect, it } from 'vitest'
import type { Member, ProjectCpm, ProjectFull, ProjectSchedule } from '@/lib/api/schemas'
import { buildPlan, edgeKey } from './plan'

const full = {
  epics: [
    { id: 2, title: 'Release', position: 1 },
    { id: 1, title: 'Auth', position: 0 },
    { id: 3, title: 'Empty', position: 2 },
  ],
  tasks: [
    { id: 1, title: 'A', epic_id: 1, status: 'done' },
    { id: 2, title: 'B', epic_id: 2, status: 'todo' },
    { id: 3, title: 'C', epic_id: 1, status: 'todo' },
  ],
  dependencies: [
    { pred_task_id: 1, succ_task_id: 2 },
    { pred_task_id: 3, succ_task_id: 2 },
  ],
} as ProjectFull

const row = (task_id: number, critical: boolean) => ({
  task_id,
  duration_hours: 8,
  es: 0,
  ef: 8,
  ls: 0,
  lf: 8,
  total_slack: critical ? 0 : 16,
  free_slack: 0,
  critical,
})

const cpm = {
  critical_paths: [[1, 2]],
  tasks: [row(1, true), row(3, false), row(2, true)],
} as ProjectCpm

const schedule = {
  start: '2026-11-02',
  finish: '2026-11-10',
  deadline: '2026-11-09',
  tasks: [
    { task_id: 1, member_id: 7, start: '2026-11-02', end: '2026-11-03', resource_delay_days: 0 },
    { task_id: 2, member_id: null, start: '2026-11-05', end: '2026-11-10', resource_delay_days: 2 },
    { task_id: 3, member_id: 7, start: '2026-11-01', end: '2026-11-03', resource_delay_days: 0 },
  ],
} as ProjectSchedule

const members = [{ id: 7, name: 'Meera Iyer' }] as Member[]

describe('buildPlan', () => {
  const plan = buildPlan(full, cpm, schedule, members)

  it('joins CPM, schedule and owner onto each task', () => {
    expect(plan.byId.get(1)).toMatchObject({
      title: 'A',
      critical: true,
      start: '2026-11-02',
      ownerName: 'Meera Iyer',
    })
    expect(plan.byId.get(2)).toMatchObject({
      ownerId: undefined,
      ownerName: undefined,
      resourceDelayDays: 2,
    })
  })

  it('links predecessors and successors both ways', () => {
    expect(plan.byId.get(2)?.predecessors).toEqual([1, 3])
    expect(plan.byId.get(1)?.successors).toEqual([2])
  })

  it('orders epics by position, drops empty ones, and sorts tasks by start', () => {
    expect(plan.epics.map((group) => group.epic.title)).toEqual(['Auth', 'Release'])
    expect(plan.epics[0].tasks.map((task) => task.id)).toEqual([3, 1])
  })

  it('marks only edges on a critical path as critical', () => {
    expect(plan.criticalEdges.has(edgeKey(1, 2))).toBe(true)
    expect(plan.criticalEdges.has(edgeKey(3, 2))).toBe(false)
  })

  it('leaves out a task the schedule has not placed', () => {
    const partial = buildPlan(full, cpm, { ...schedule, tasks: schedule.tasks.slice(0, 2) }, members)
    expect(partial.byId.has(3)).toBe(false)
    expect(partial.edges).toEqual([{ pred: 1, succ: 2 }])
  })
})
