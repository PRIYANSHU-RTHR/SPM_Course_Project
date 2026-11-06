import { describe, expect, it } from 'vitest'
import {
  daysUntil,
  formatDate,
  formatDaysLeft,
  formatDelta,
  formatHours,
  formatLakh,
  formatPercent,
  formatProjectId,
  formatRatio,
  formatRupees,
  formatShortDate,
  formatTaskId,
  initials,
} from './format'

describe('format', () => {
  it('formats hours', () => {
    expect(formatHours(12)).toBe('12h')
    expect(formatHours(12.46)).toBe('12.5h')
    expect(formatHours(0)).toBe('0h')
  })

  it('formats a 0–1 ratio as a percent', () => {
    expect(formatPercent(0.814)).toBe('81%')
    expect(formatPercent(0.814, 1)).toBe('81.4%')
    expect(formatPercent(0)).toBe('0%')
  })

  it('formats rupees with Indian grouping from numbers and Decimal strings', () => {
    expect(formatRupees(1250000)).toBe('₹12,50,000')
    expect(formatRupees('620000.00')).toBe('₹6,20,000')
    expect(formatRupees('850.50', 2)).toBe('₹850.50')
  })

  it('reads date-only strings as local dates', () => {
    expect(formatDate('2026-12-18')).toBe('18 Dec 2026')
    expect(formatShortDate('2026-01-01')).toBe('01 Jan')
  })

  it('formats task ids', () => {
    expect(formatTaskId(14)).toBe('T-014')
    expect(formatTaskId(1234)).toBe('T-1234')
  })

  it('formats project ids and ratios', () => {
    expect(formatProjectId(3)).toBe('P-003')
    expect(formatRatio(0.9389)).toBe('0.94')
    expect(formatRatio(null)).toBe('—')
  })

  it('formats signed deltas with a real minus sign', () => {
    expect(formatDelta(0.014)).toBe('+0.01')
    expect(formatDelta(-0.02)).toBe('−0.02')
    expect(formatDelta(-0.001)).toBe('±0.00')
    expect(formatDelta(null)).toBeUndefined()
  })

  it('counts calendar days left and phrases them', () => {
    const today = new Date(2026, 10, 6, 15, 30)
    expect(daysUntil('2026-12-01', today)).toBe(25)
    expect(daysUntil('2026-11-06', today)).toBe(0)
    expect(daysUntil('2026-11-03', today)).toBe(-3)
    expect(formatDaysLeft(25)).toBe('25 days left')
    expect(formatDaysLeft(1)).toBe('1 day left')
    expect(formatDaysLeft(0)).toBe('Due today')
    expect(formatDaysLeft(-3)).toBe('3 days overdue')
  })

  it('formats lakh for chart axes', () => {
    expect(formatLakh(450000)).toBe('₹4.5L')
    expect(formatLakh(300000)).toBe('₹3L')
  })

  it('builds initials', () => {
    expect(initials('Meera Iyer')).toBe('MI')
    expect(initials('Meera')).toBe('M')
  })

  it('shows a dash for missing values', () => {
    expect(formatHours(null)).toBe('—')
    expect(formatPercent(undefined)).toBe('—')
    expect(formatRupees(null)).toBe('—')
    expect(formatRupees('not a number')).toBe('—')
    expect(formatDate(null)).toBe('—')
    expect(formatDate('garbage')).toBe('—')
    expect(formatTaskId(null)).toBe('—')
  })
})
