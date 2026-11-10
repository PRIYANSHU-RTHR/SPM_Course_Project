/** Pure helpers for the disruption simulator, approvals inbox and audit timeline. */
import type { AuditEntry, ProposalItem } from '@/lib/api/schemas'
import { formatShortDate, formatTaskId } from '@/lib/format'

export const REASON_LABEL: Record<ProposalItem['reasons'][number], string> = {
  owner_unavailable: 'owner away',
  critical_slip: 'critical slip',
  new_scope: 'new scope',
}

type Names = { member: (id: number) => string; task: (id: number) => string }

const num = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined
const str = (value: unknown): string | undefined => (typeof value === 'string' ? value : undefined)

/** One readable line for the disruption stored on a proposal. */
export function describeDisruption(disruption: Record<string, unknown>, names: Names): string {
  switch (disruption.type) {
    case 'leave': {
      const member = num(disruption.member_id)
      return `${member === undefined ? 'A member' : names.member(member)} on leave ${formatShortDate(
        str(disruption.start_date),
      )} – ${formatShortDate(str(disruption.end_date))}`
    }
    case 'slip': {
      const task = num(disruption.task_id)
      const hours = num(disruption.extra_hours)
      return `${task === undefined ? 'A task' : names.task(task)} needs ${hours ?? '?'} h more`
    }
    case 'scope_add': {
      const task = disruption.task as Record<string, unknown> | undefined
      return `New scope: ${str(task?.title) ?? 'untitled task'}`
    }
    default:
      return 'Disruption'
  }
}

/** Task label for tables: `T-012 Payment gateway integration`. */
export function taskLabel(id: number, title: string | undefined): string {
  return title ? `${formatTaskId(id)} ${title}` : formatTaskId(id)
}

/** Change in percentage points, e.g. 0.30 -> 0.11 = -19. Null if either side is unknown. */
export function pointsDelta(before: number | null, after: number | null): number | null {
  if (before === null || after === null) return null
  return Math.round((after - before) * 100)
}

export function formatPoints(delta: number | null): string {
  if (delta === null || delta === 0) return ''
  return `${delta > 0 ? '+' : '−'}${Math.abs(delta)} pts`
}

export interface AuditDay {
  day: string
  entries: AuditEntry[]
}

/** Newest first, grouped by UTC day (the API stores UTC). */
export function groupByDay(entries: AuditEntry[]): AuditDay[] {
  const days: AuditDay[] = []
  for (const entry of entries) {
    const day = entry.created_at.slice(0, 10)
    const last = days.at(-1)
    if (last && last.day === day) last.entries.push(entry)
    else days.push({ day, entries: [entry] })
  }
  return days
}

/** People act; the risk engine and agents are `system:*`. */
export function isSystemActor(actor: string): boolean {
  return actor.startsWith('system:')
}
