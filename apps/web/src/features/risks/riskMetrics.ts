/** Shapes the risk register for display. Scores come from the API. */
import type { Risk } from '@/lib/api/schemas'

export interface RmmmPlan {
  mitigation: string
  monitoringTrigger: string
  contingency: string
  ownerRole: string
  source: 'model' | 'template' | undefined
  grounded: boolean | undefined
}

export interface Cell {
  probability: number
  impact: number
}

const text = (value: unknown) => (typeof value === 'string' ? value : '')

/** The stored plan, or null when the risk has none. */
export function parseRmmm(rmmm: Risk['rmmm']): RmmmPlan | null {
  if (!rmmm || !text(rmmm.mitigation)) return null
  const source = rmmm.source === 'model' || rmmm.source === 'template' ? rmmm.source : undefined
  return {
    mitigation: text(rmmm.mitigation),
    monitoringTrigger: text(rmmm.monitoring_trigger),
    contingency: text(rmmm.contingency),
    ownerRole: text(rmmm.owner_role),
    source,
    grounded: typeof rmmm.grounded === 'boolean' ? rmmm.grounded : undefined,
  }
}

export const cellKey = ({ probability, impact }: Cell) => `${probability}-${impact}`

/** Risks still being tracked, counted per probability × impact cell. */
export function cellCounts(risks: Risk[]): Map<string, number> {
  const counts = new Map<string, number>()
  for (const risk of risks) {
    if (risk.status === 'closed') continue
    const key = cellKey(risk)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return counts
}

/** Register order: tracked risks by score, then closed ones. */
export function sortRegister(risks: Risk[]): Risk[] {
  return [...risks].sort(
    (a, b) =>
      Number(a.status === 'closed') - Number(b.status === 'closed') ||
      b.score - a.score ||
      a.id - b.id,
  )
}

/** A selected cell shows its tracked risks, matching the count printed on the cell. */
export function filterByCell(risks: Risk[], cell: Cell | null): Risk[] {
  if (!cell) return risks
  return risks.filter(
    (risk) =>
      risk.status !== 'closed' &&
      risk.probability === cell.probability &&
      risk.impact === cell.impact,
  )
}

/** Tint strength for a score of 1–25, as a percentage. */
export function cellTint(score: number): number {
  return Math.round(6 + ((score - 1) / 24) * 46)
}

/** "criticality_index" → "Criticality index". */
export function evidenceLabel(key: string): string {
  const words = key.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function evidenceValue(value: unknown): string {
  if (typeof value === 'number') return String(Number(value.toFixed(2)))
  if (value === null || value === undefined) return '—'
  return String(value)
}
