import { describe, expect, it } from 'vitest'
import type { ProjectForecast, Task } from '@/lib/api/schemas'
import { axisTicks, histogramBars, percentileMarks, topCriticality } from './forecastData'

const forecast = {
  deadline_hours: 30,
  histogram: [
    { start_hours: 10, runs: 4 },
    { start_hours: 20, runs: 9 },
    { start_hours: 30, runs: 2 },
  ],
  p50: { hours: 22, on: '2026-11-30' },
  p80: { hours: 28, on: '2026-12-01' },
  p95: { hours: 33, on: '2026-12-03' },
  criticality: { '1': 1, '2': 0.25, '3': 1, '4': 0.5 },
} as unknown as ProjectForecast

describe('histogramBars', () => {
  const bars = histogramBars(forecast)

  it('centres each bar on its bin', () => {
    expect(bars[0]).toMatchObject({ start: 10, end: 20, mid: 15, runs: 4 })
  })

  it('marks a bin on time only when it ends by the deadline', () => {
    expect(bars.map((bar) => bar.onTime)).toEqual([true, true, false])
  })

  it('handles a single bin', () => {
    const one = { ...forecast, histogram: [{ start_hours: 10, runs: 5 }] } as ProjectForecast
    expect(histogramBars(one)).toHaveLength(1)
  })
})

describe('percentileMarks', () => {
  it('keeps each percentile with its level and date', () => {
    expect(percentileMarks(forecast)[1]).toEqual({
      label: 'P80',
      probability: 0.8,
      hours: 28,
      date: '2026-12-01',
    })
  })
})

describe('topCriticality', () => {
  const tasks = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }] as Task[]

  it('sorts by index, then task order, and limits the list', () => {
    const rows = topCriticality(forecast, tasks, 3)
    expect(rows.map((row) => row.task.id)).toEqual([1, 3, 4])
  })

  it('treats a missing index as zero', () => {
    expect(topCriticality(forecast, tasks).at(-1)).toMatchObject({ index: 0 })
  })
})

describe('axisTicks', () => {
  it('spreads ticks evenly from end to end', () => {
    expect(axisTicks(0, 100, 5)).toEqual([0, 25, 50, 75, 100])
  })
})
