import { describe, expect, it } from 'vitest'
import type { Risk } from '@/lib/api/schemas'
import {
  cellCounts,
  cellTint,
  evidenceLabel,
  evidenceValue,
  filterByCell,
  parseRmmm,
  sortRegister,
} from './riskMetrics'

const risk = (partial: Partial<Risk>) =>
  ({ id: 1, probability: 3, impact: 3, score: 9, status: 'open', ...partial }) as Risk

describe('parseRmmm', () => {
  it('reads the Step 16 plan format', () => {
    expect(
      parseRmmm({
        mitigation: 'Pair up',
        monitoring_trigger: 'Slips a day',
        contingency: 'Reassign',
        owner_role: 'Project manager',
        grounded: true,
        source: 'model',
      }),
    ).toEqual({
      mitigation: 'Pair up',
      monitoringTrigger: 'Slips a day',
      contingency: 'Reassign',
      ownerRole: 'Project manager',
      grounded: true,
      source: 'model',
    })
  })

  it('treats a missing or empty plan as none', () => {
    expect(parseRmmm(null)).toBeNull()
    expect(parseRmmm({})).toBeNull()
  })
})

describe('matrix', () => {
  const risks = [
    risk({ id: 1 }),
    risk({ id: 2 }),
    risk({ id: 3, status: 'closed' }),
    risk({ id: 4, status: 'mitigating', probability: 5, impact: 5, score: 25 }),
  ]

  it('counts tracked risks per cell and skips closed ones', () => {
    const counts = cellCounts(risks)
    expect(counts.get('3-3')).toBe(2)
    expect(counts.get('5-5')).toBe(1)
    expect(counts.get('1-1')).toBeUndefined()
  })

  it('filters to a cell, matching its count', () => {
    const cell = { probability: 3, impact: 3 }
    expect(filterByCell(risks, cell).map((item) => item.id)).toEqual([1, 2])
    expect(filterByCell(risks, null)).toHaveLength(4)
  })

  it('tints higher scores more strongly', () => {
    expect(cellTint(1)).toBe(6)
    expect(cellTint(25)).toBe(52)
    expect(cellTint(16)).toBeGreaterThan(cellTint(4))
  })
})

describe('sortRegister', () => {
  it('sorts by score and keeps closed risks last', () => {
    const sorted = sortRegister([
      risk({ id: 1, score: 25, status: 'closed' }),
      risk({ id: 2, score: 6 }),
      risk({ id: 3, score: 12 }),
      risk({ id: 4, score: 6 }),
    ])
    expect(sorted.map((item) => item.id)).toEqual([3, 2, 4, 1])
  })
})

describe('evidence', () => {
  it('formats keys and values', () => {
    expect(evidenceLabel('criticality_index')).toBe('Criticality index')
    expect(evidenceValue(32.6667)).toBe('32.67')
    expect(evidenceValue(1)).toBe('1')
    expect(evidenceValue(null)).toBe('—')
    expect(evidenceValue('T-012')).toBe('T-012')
  })
})
