import { describe, expect, it } from 'vitest'
import type {
  Member,
  ProjectFull,
  RecommendResponse,
  ScheduledTask,
  Score,
  WeekLoad,
} from '@/lib/api/schemas'
import {
  assignmentRows,
  busFactorSkills,
  compareModes,
  heatShare,
  levelOf,
  loadKey,
  loadsByCell,
  skillNames,
  storedScore,
  toBreakdown,
  weekStarts,
  weekTasks,
} from './teamMetrics'

const member = (id: number, name: string, skills: Record<string, number>) =>
  ({
    id,
    name,
    skills: Object.entries(skills).map(([skill, level]) => ({ skill, level })),
  }) as Member

const members = [
  member(1, 'Aarav', { payments: 4, react: 2 }),
  member(2, 'Diya', { payments: 3, react: 4, docker: 5 }),
  member(3, 'Meera', { react: 5, docker: 4 }),
]

describe('skills', () => {
  it('lists skills alphabetically, once each', () => {
    expect(skillNames(members)).toEqual(['docker', 'payments', 'react'])
  })

  it('reads a missing skill as level 0', () => {
    expect(levelOf(members[0], 'docker')).toBe(0)
  })

  it('flags a skill with exactly one person at level 4+', () => {
    expect([...busFactorSkills(members)]).toEqual([['payments', 'Aarav']])
  })

  it('does not flag a skill nobody has at level 4', () => {
    expect(busFactorSkills([member(1, 'A', { sql: 3 })]).size).toBe(0)
  })
})

describe('capacity', () => {
  const loads = [
    { member_id: 1, week_start: '2026-11-09', utilisation: 1.2 },
    { member_id: 1, week_start: '2026-11-02', utilisation: 0.5 },
  ] as WeekLoad[]

  it('lists weeks in order and finds a cell', () => {
    expect(weekStarts(loads)).toEqual(['2026-11-02', '2026-11-09'])
    expect(loadsByCell(loads).get(loadKey(1, '2026-11-09'))?.utilisation).toBe(1.2)
  })

  it('caps the tint so a heavy week stays readable', () => {
    expect(heatShare(0)).toBe(0)
    expect(heatShare(0.5)).toBe(31)
    expect(heatShare(3)).toBe(62)
  })

  it('finds tasks overlapping a week, for that member only', () => {
    const tasks = [
      { task_id: 1, member_id: 1, start: '2026-10-30', end: '2026-11-02' },
      { task_id: 2, member_id: 1, start: '2026-11-08', end: '2026-11-10' },
      { task_id: 3, member_id: 1, start: '2026-11-09', end: '2026-11-10' },
      { task_id: 4, member_id: 2, start: '2026-11-03', end: '2026-11-04' },
      { task_id: 5, member_id: null, start: '2026-11-03', end: '2026-11-04' },
    ] as ScheduledTask[]
    expect(weekTasks(tasks, 1, '2026-11-02').map((task) => task.task_id)).toEqual([1, 2])
  })
})

describe('scores', () => {
  it('reads seeded and engine shapes', () => {
    expect(storedScore({ score: 91.5 })).toBe(91.5)
    expect(storedScore({ total: 80 })).toBe(80)
    expect(storedScore({})).toBeNull()
  })

  it('stores both key names', () => {
    expect(toBreakdown({ total: 80 } as Score)).toMatchObject({ total: 80, score: 80 })
    expect(toBreakdown(null)).toEqual({})
  })
})

describe('assignmentRows', () => {
  it('joins tasks to their owner and recommendation, in id order', () => {
    const full = {
      tasks: [{ id: 2 }, { id: 1 }],
      assignments: [{ task_id: 1, member_id: 7 }],
    } as ProjectFull
    const recommend = { recommendations: [{ task_id: 2, member_id: 3 }] } as RecommendResponse
    const rows = assignmentRows(full, recommend)
    expect(rows.map((row) => row.task.id)).toEqual([1, 2])
    expect(rows[0].assignment?.member_id).toBe(7)
    expect(rows[1].assignment).toBeUndefined()
    expect(rows[1].recommendation?.member_id).toBe(3)
  })

  it('still lists tasks while recommendations load', () => {
    const full = { tasks: [{ id: 1 }], assignments: [] } as unknown as ProjectFull
    expect(assignmentRows(full, undefined)[0].recommendation).toBeUndefined()
  })
})

describe('compareModes', () => {
  const rows = compareModes({
    greedy_total: 2248.48,
    optimal_total: 2236.95,
    greedy_utilisation_std: 0.12,
    optimal_utilisation_std: 0.13,
    greedy_unassigned: 0,
    optimal_unassigned: 0,
  })

  it('reports optimal minus greedy, even when optimal is lower', () => {
    expect(rows[0]).toMatchObject({ greedy: '2,248', optimal: '2,237' })
    expect(rows[0].delta).toBeCloseTo(-11.53)
    expect(rows[1].optimal).toBe('0.13')
    expect(rows[2].delta).toBe(0)
  })
})
