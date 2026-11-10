import { describe, expect, it } from 'vitest'
import type { Plan, PlanTask } from './plan'
import { barSpan, buildRows, buildTimeline, DAY_WIDTH, dayX, dependencyPath, slackEnd } from './timeline'

const task = (partial: Partial<PlanTask>): PlanTask =>
  ({ id: 1, title: 'A', start: '2026-11-02', end: '2026-11-03', totalSlack: 0, ...partial }) as PlanTask

const plan = {
  start: '2026-11-02',
  finish: '2026-11-13',
  deadline: '2026-11-11',
  tasks: [task({})],
  epics: [{ epic: { id: 1, title: 'Auth' }, tasks: [task({}), task({ id: 2 })] }],
} as unknown as Plan

describe('buildTimeline', () => {
  const timeline = buildTimeline(plan, '2026-11-04')

  it('starts at the project start and passes the finish', () => {
    expect(timeline.first).toBe('2026-11-02')
    expect(timeline.days.at(-1)! > plan.finish).toBe(true)
  })

  it('lists Mondays and weekends', () => {
    expect(timeline.mondays.slice(0, 2)).toEqual(['2026-11-02', '2026-11-09'])
    expect(timeline.weekends.slice(0, 2)).toEqual(['2026-11-07', '2026-11-08'])
  })

  it('stretches to show a today outside the project', () => {
    expect(buildTimeline(plan, '2026-10-30').first).toBe('2026-10-30')
    expect(buildTimeline(plan, '2026-12-25').days).toContain('2026-12-25')
  })
})

describe('bars', () => {
  const timeline = buildTimeline(plan, '2026-11-04')

  it('covers the whole end day', () => {
    expect(barSpan(timeline, task({}), 'day')).toEqual({
      left: 0,
      width: 2 * DAY_WIDTH.day,
      tail: 0,
    })
  })

  it('draws slack as working days after the bar, skipping the weekend', () => {
    const late = task({ start: '2026-11-05', end: '2026-11-06', totalSlack: 8 })
    expect(slackEnd(late)).toBe('2026-11-09')
    expect(barSpan(timeline, late, 'week').tail).toBe(3 * DAY_WIDTH.week)
  })

  it('scales with zoom', () => {
    expect(dayX(timeline, '2026-11-09', 'day')).toBe(7 * DAY_WIDTH.day)
    expect(dayX(timeline, '2026-11-09', 'week')).toBe(7 * DAY_WIDTH.week)
  })
})

describe('rows', () => {
  it('puts each epic header before its tasks', () => {
    expect(buildRows(plan).map((row) => row.key)).toEqual(['epic-1', 'task-1', 'task-2'])
  })
})

describe('dependencyPath', () => {
  it('bends just before the successor when there is room', () => {
    expect(dependencyPath({ x: 10, row: 0 }, { x: 100, row: 2 })).toBe('M 10 16 H 94 V 80 H 100')
  })

  it('still leaves the predecessor first when the successor starts earlier', () => {
    expect(dependencyPath({ x: 100, row: 2 }, { x: 40, row: 0 })).toBe('M 100 80 H 106 V 16 H 40')
  })
})
