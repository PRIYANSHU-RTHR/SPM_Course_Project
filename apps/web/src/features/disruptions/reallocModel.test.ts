import { describe, expect, it } from 'vitest'
import type { AuditEntry } from '@/lib/api/schemas'
import {
  describeDisruption,
  formatPoints,
  groupByDay,
  isSystemActor,
  pointsDelta,
  taskLabel,
} from './reallocModel'

const names = {
  member: (id: number) => (id === 1 ? 'Aarav Mehta' : `Member ${id}`),
  task: (id: number) => taskLabel(id, id === 12 ? 'Payment gateway integration' : undefined),
}

describe('describeDisruption', () => {
  it('reads leave, slip and new scope', () => {
    expect(
      describeDisruption(
        { type: 'leave', member_id: 1, start_date: '2026-11-09', end_date: '2026-11-20' },
        names,
      ),
    ).toBe('Aarav Mehta on leave 09 Nov – 20 Nov')
    expect(describeDisruption({ type: 'slip', task_id: 12, extra_hours: 16 }, names)).toBe(
      'T-012 Payment gateway integration needs 16 h more',
    )
    expect(describeDisruption({ type: 'scope_add', task: { title: 'UPI refunds' } }, names)).toBe(
      'New scope: UPI refunds',
    )
    expect(describeDisruption({ type: 'other' }, names)).toBe('Disruption')
  })
})

describe('metric deltas', () => {
  it('reports percentage points', () => {
    expect(pointsDelta(0.3, 0.11)).toBe(-19)
    expect(pointsDelta(null, 0.5)).toBeNull()
    expect(formatPoints(-19)).toBe('−19 pts')
    expect(formatPoints(8)).toBe('+8 pts')
    expect(formatPoints(0)).toBe('')
  })
})

describe('audit', () => {
  const entry = (id: number, at: string, actor = 'PM'): AuditEntry => ({
    id,
    actor,
    action: 'x',
    entity: 'project',
    entity_id: 1,
    before: null,
    after: null,
    reason: null,
    created_at: at,
    summary: `entry ${id}`,
  })

  it('groups newest-first entries by day', () => {
    const days = groupByDay([
      entry(3, '2026-11-10T09:00:00Z'),
      entry(2, '2026-11-10T08:00:00Z'),
      entry(1, '2026-11-09T17:00:00Z'),
    ])
    expect(days.map((d) => [d.day, d.entries.map((e) => e.id)])).toEqual([
      ['2026-11-10', [3, 2]],
      ['2026-11-09', [1]],
    ])
  })

  it('tells system actors from people', () => {
    expect(isSystemActor('system:risk-engine')).toBe(true)
    expect(isSystemActor('pm:asha')).toBe(false)
  })
})
