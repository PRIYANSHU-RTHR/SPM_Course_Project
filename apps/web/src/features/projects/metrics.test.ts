import { describe, expect, it } from 'vitest'
import type { ProjectCpm, ProjectEvm, ProjectFull, Risk, WeekLoad } from '@/lib/api/schemas'
import {
  evmDeltas,
  hasPlan,
  nextCritical,
  openRisks,
  overloadedMembers,
  progress,
  sCurve,
} from './metrics'

function evm(partial: Partial<ProjectEvm>): ProjectEvm {
  return { bac: '1000.00', ev: '250.00', snapshots: [], planned: [], ...partial } as ProjectEvm
}

describe('progress', () => {
  it('is earned value over budget at completion', () => {
    expect(progress(evm({}))).toBe(0.25)
  })

  it('is unknown for a project with no planned work', () => {
    expect(hasPlan(evm({ bac: '0.00' }))).toBe(false)
    expect(progress(evm({ bac: '0.00' }))).toBeNull()
  })
})

describe('overloadedMembers', () => {
  it('counts each member once and leaves exactly 100% out', () => {
    const loads = [
      { member_id: 1, utilisation: 1.2 },
      { member_id: 1, utilisation: 1.4 },
      { member_id: 2, utilisation: 1 },
      { member_id: 3, utilisation: 0.5 },
    ] as WeekLoad[]
    expect(overloadedMembers(loads)).toBe(1)
  })
})

describe('openRisks', () => {
  it('drops closed risks and sorts by score, then id', () => {
    const risks = [
      { id: 1, status: 'open', score: 6 },
      { id: 2, status: 'closed', score: 25 },
      { id: 3, status: 'mitigating', score: 15 },
      { id: 4, status: 'open', score: 6 },
    ] as Risk[]
    expect(openRisks(risks).map((risk) => risk.id)).toEqual([3, 1, 4])
  })
})

describe('nextCritical', () => {
  const full = {
    tasks: [
      { id: 1, status: 'done' },
      { id: 2, status: 'in_progress' },
      { id: 3, status: 'todo' },
      { id: 4, status: 'todo' },
    ],
    assignments: [{ task_id: 2, member_id: 7 }],
  } as ProjectFull
  const cpm = {
    tasks: [
      { task_id: 1, critical: true, duration_hours: 5 },
      { task_id: 2, critical: true, duration_hours: 6 },
      { task_id: 3, critical: false, duration_hours: 7 },
      { task_id: 4, critical: true, duration_hours: 8 },
    ],
  } as ProjectCpm

  it('keeps unfinished critical tasks in dependency order with their owner', () => {
    const rows = nextCritical(cpm, full)
    expect(rows.map((row) => row.task.id)).toEqual([2, 4])
    expect(rows[0]).toMatchObject({ hours: 6, ownerId: 7 })
    expect(rows[1].ownerId).toBeUndefined()
  })

  it('respects the limit', () => {
    expect(nextCritical(cpm, full, 1)).toHaveLength(1)
  })
})

describe('evmDeltas', () => {
  it('compares the last two snapshots', () => {
    const deltas = evmDeltas(
      evm({
        snapshots: [
          { on: '2026-11-05', pv: '100.00', ev: '90.00', ac: '100.00' },
          { on: '2026-11-06', pv: '100.00', ev: '95.00', ac: '95.00' },
        ],
      }),
    )
    expect(deltas.spi).toBeCloseTo(0.05)
    expect(deltas.cpi).toBeCloseTo(0.1)
  })

  it('has nothing to compare with a single snapshot or a zero divisor', () => {
    expect(evmDeltas(evm({ snapshots: [] }))).toEqual({ spi: null, cpi: null })
    const deltas = evmDeltas(
      evm({
        snapshots: [
          { on: '2026-11-05', pv: '0.00', ev: '0.00', ac: '0.00' },
          { on: '2026-11-06', pv: '10.00', ev: '10.00', ac: '10.00' },
        ],
      }),
    )
    expect(deltas).toEqual({ spi: null, cpi: null })
  })
})

describe('sCurve', () => {
  it('merges planned and recorded points by date, keeping recorded values', () => {
    const points = sCurve(
      evm({
        planned: [
          { on: '2026-11-13', pv: '300.00', ev: null, ac: null },
          { on: '2026-11-06', pv: '200.00', ev: null, ac: null },
        ],
        snapshots: [{ on: '2026-11-06', pv: '200.00', ev: '190.00', ac: '180.00' }],
      }),
    )
    expect(points.map((point) => point.on)).toEqual(['2026-11-06', '2026-11-13'])
    expect(points[0]).toMatchObject({ pv: 200, ev: 190, ac: 180 })
    expect(points[1]).toMatchObject({ pv: 300, ev: null, ac: null })
  })
})
