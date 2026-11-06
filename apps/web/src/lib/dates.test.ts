import { describe, expect, it } from 'vitest'
import {
  addDays,
  addWorkingDays,
  dateAfterHours,
  daysBetween,
  isMonday,
  isWeekend,
  slackDays,
  todayIso,
  workingDaysBetween,
} from './dates'

describe('dates', () => {
  it('adds calendar days across a month end', () => {
    expect(addDays('2026-11-30', 1)).toBe('2026-12-01')
    expect(addDays('2026-12-01', -1)).toBe('2026-11-30')
    expect(daysBetween('2026-11-30', '2026-12-02')).toBe(2)
  })

  it('knows weekends and Mondays', () => {
    expect(isWeekend('2026-11-07')).toBe(true)
    expect(isWeekend('2026-11-08')).toBe(true)
    expect(isWeekend('2026-11-06')).toBe(false)
    expect(isMonday('2026-11-09')).toBe(true)
  })

  it('counts working days, skipping weekends', () => {
    expect(workingDaysBetween('2026-12-01', '2026-12-07')).toBe(4)
    expect(workingDaysBetween('2026-12-07', '2026-12-01')).toBe(-4)
    expect(workingDaysBetween('2026-12-01', '2026-12-01')).toBe(0)
  })

  it('adds working days, skipping weekends', () => {
    expect(addWorkingDays('2026-11-06', 1)).toBe('2026-11-09')
    expect(addWorkingDays('2026-11-06', 0)).toBe('2026-11-06')
  })

  it('converts project hours to a finish date on the 8-hour calendar', () => {
    expect(dateAfterHours('2026-11-02', 4)).toBe('2026-11-02')
    expect(dateAfterHours('2026-11-02', 8)).toBe('2026-11-02')
    expect(dateAfterHours('2026-11-02', 8.5)).toBe('2026-11-03')
    expect(dateAfterHours('2026-11-02', 48)).toBe('2026-11-09')
    expect(dateAfterHours('2026-11-02', 0)).toBe('2026-11-02')
  })

  it('rounds slack up to whole days', () => {
    expect(slackDays(0)).toBe(0)
    expect(slackDays(0.5)).toBe(1)
    expect(slackDays(8)).toBe(1)
    expect(slackDays(8.1)).toBe(2)
  })

  it('reads today from the local clock', () => {
    expect(todayIso(new Date(2026, 10, 6, 23, 30))).toBe('2026-11-06')
  })
})
