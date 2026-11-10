/** Turns engine responses into what the project pages show. No formulas of its own beyond ratios. */
import type {
  ProjectCpm,
  ProjectEvm,
  ProjectFull,
  Risk,
  Task,
  WeekLoad,
} from '@/lib/api/schemas'

/** Below 0.9 matches the risk engine's SPI and CPI rule; below 1 is behind plan. */
export function indexStatus(value: number | null | undefined) {
  if (value == null) return undefined
  if (value < 0.9) return 'danger'
  return value < 1 ? 'warning' : undefined
}

/** Below 60% matches the risk engine's P(on time) rule. */
export function forecastStatus(value: number) {
  if (value < 0.6) return 'danger'
  return value < 0.8 ? 'warning' : undefined
}

export function hasPlan(evm: ProjectEvm): boolean {
  return Number(evm.bac) > 0
}

/** Share of the budget at completion earned so far, 0–1. */
export function progress(evm: ProjectEvm): number | null {
  return hasPlan(evm) ? Number(evm.ev) / Number(evm.bac) : null
}

/** Members above 100% utilisation in at least one ISO week. */
export function overloadedMembers(loads: WeekLoad[]): number {
  return new Set(loads.filter((week) => week.utilisation > 1).map((week) => week.member_id)).size
}

/** Risks the register still tracks: `mitigating` counts, `closed` does not. Highest score first. */
export function openRisks(risks: Risk[]): Risk[] {
  return risks
    .filter((risk) => risk.status !== 'closed')
    .sort((a, b) => b.score - a.score || a.id - b.id)
}

export interface CriticalRow {
  task: Task
  hours: number
  ownerId: number | undefined
}

/** Unfinished critical tasks in dependency order. */
export function nextCritical(cpm: ProjectCpm, full: ProjectFull, limit = 5): CriticalRow[] {
  const tasks = new Map(full.tasks.map((task) => [task.id, task]))
  const owners = new Map(full.assignments.map((item) => [item.task_id, item.member_id]))
  const rows: CriticalRow[] = []
  for (const row of cpm.tasks) {
    const task = tasks.get(row.task_id)
    if (row.critical && task && task.status !== 'done') {
      rows.push({ task, hours: row.duration_hours, ownerId: owners.get(task.id) })
    }
  }
  return rows.slice(0, limit)
}

/** Change in SPI and CPI since the snapshot before the latest one. */
export function evmDeltas(evm: ProjectEvm): { spi: number | null; cpi: number | null } {
  const [previous, latest] = evm.snapshots.slice(-2)
  if (!previous || !latest) return { spi: null, cpi: null }
  const ratio = (top: string | null | undefined, bottom: string | null | undefined) => {
    const divisor = Number(bottom)
    return top == null || !divisor ? null : Number(top) / divisor
  }
  const delta = (now: number | null, before: number | null) =>
    now === null || before === null ? null : now - before
  return {
    spi: delta(ratio(latest.ev, latest.pv), ratio(previous.ev, previous.pv)),
    cpi: delta(ratio(latest.ev, latest.ac), ratio(previous.ev, previous.ac)),
  }
}

export interface CurvePoint {
  /** Milliseconds at UTC midnight, for a time axis. */
  time: number
  on: string
  pv: number | null
  ev: number | null
  ac: number | null
}

export function dateToTime(date: string): number {
  return new Date(`${date}T00:00:00Z`).getTime()
}

/** Recorded snapshots plus the weekly planned curve, one point per date. */
export function sCurve(evm: ProjectEvm): CurvePoint[] {
  const points = new Map<string, CurvePoint>()
  for (const point of [...evm.planned, ...evm.snapshots]) {
    points.set(point.on, {
      time: dateToTime(point.on),
      on: point.on,
      pv: Number(point.pv),
      ev: point.ev == null ? null : Number(point.ev),
      ac: point.ac == null ? null : Number(point.ac),
    })
  }
  return [...points.values()].sort((a, b) => a.time - b.time)
}
