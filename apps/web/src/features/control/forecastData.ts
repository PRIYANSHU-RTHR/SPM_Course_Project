/** Shapes the Monte Carlo response for charts. Every number comes from the engine. */
import type { ProjectForecast, Task } from '@/lib/api/schemas'
import { dateAfterHours } from '@/lib/dates'

export interface HistogramBar {
  mid: number
  start: number
  end: number
  runs: number
  onTime: boolean
}

export function histogramBars(forecast: ProjectForecast): HistogramBar[] {
  const bins = forecast.histogram
  const width = bins.length > 1 ? bins[1].start_hours - bins[0].start_hours : 1
  return bins.map((bin) => {
    const end = bin.start_hours + width
    return {
      mid: bin.start_hours + width / 2,
      start: bin.start_hours,
      end,
      runs: bin.runs,
      onTime: end <= forecast.deadline_hours,
    }
  })
}

export function axisTicks(min: number, max: number, count = 5): number[] {
  return Array.from({ length: count }, (_, index) => min + ((max - min) * index) / (count - 1))
}

export interface PercentileMark {
  label: string
  probability: number
  hours: number
  date: string
}

export function percentileMarks(forecast: ProjectForecast): PercentileMark[] {
  return (
    [
      ['P50', 0.5, forecast.p50],
      ['P80', 0.8, forecast.p80],
      ['P95', 0.95, forecast.p95],
    ] as const
  ).map(([label, probability, point]) => ({
    label,
    probability,
    hours: point.hours,
    date: point.on,
  }))
}

export interface CriticalityRow {
  task: Task
  index: number
}

/** Tasks most often on the longest path, highest first. Ties keep task order. */
export function topCriticality(
  forecast: ProjectForecast,
  tasks: Task[],
  limit = 5,
): CriticalityRow[] {
  return tasks
    .map((task) => ({ task, index: forecast.criticality[String(task.id)] ?? 0 }))
    .sort((a, b) => b.index - a.index || a.task.id - b.task.id)
    .slice(0, limit)
}

export const hoursToDate = (start: string, hours: number) => dateAfterHours(start, hours)
