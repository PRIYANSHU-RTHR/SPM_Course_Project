/** Display helpers. Every number and date in the UI goes through this file. */

const EMPTY = '—'

type Maybe<T> = T | null | undefined

function isMissing(value: Maybe<number>): value is null | undefined {
  return value === null || value === undefined || Number.isNaN(value)
}

/** 12.5 → "12.5h", 12 → "12h". */
export function formatHours(hours: Maybe<number>): string {
  if (isMissing(hours)) return EMPTY
  return `${Number(hours.toFixed(1))}h`
}

/** Ratio in 0–1, as engines return it: 0.814 → "81%". */
export function formatPercent(ratio: Maybe<number>, digits = 0): string {
  if (isMissing(ratio)) return EMPTY
  return `${(ratio * 100).toFixed(digits)}%`
}

/**
 * Rupees with Indian digit grouping: "1250000.00" → "₹12,50,000".
 * The API sends money as Decimal strings, so a string input is accepted as is.
 */
export function formatRupees(amount: Maybe<number | string>, digits = 0): string {
  const value = typeof amount === 'string' ? Number(amount) : amount
  if (isMissing(value)) return EMPTY
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
  return formatted.replace('-', '−')
}

/** Date-only strings are read as local dates, so they never shift a day across time zones. */
function parseDate(value: string): Date {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (dateOnly) return new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
  return new Date(value)
}

/** "2026-12-18" → "18 Dec 2026". */
export function formatDate(value: Maybe<string>): string {
  if (!value) return EMPTY
  const date = parseDate(value)
  if (Number.isNaN(date.getTime())) return EMPTY
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(
    date,
  )
}

/** "2026-12-18" → "18 Dec". For tables and chart labels where the year is obvious. */
export function formatShortDate(value: Maybe<string>): string {
  if (!value) return EMPTY
  const date = parseDate(value)
  if (Number.isNaN(date.getTime())) return EMPTY
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short' }).format(date)
}

/** 14 → "T-014". */
export function formatTaskId(id: Maybe<number>): string {
  if (isMissing(id)) return EMPTY
  return `T-${String(id).padStart(3, '0')}`
}

/** 3 → "P-003". */
export function formatProjectId(id: Maybe<number>): string {
  if (isMissing(id)) return EMPTY
  return `P-${String(id).padStart(3, '0')}`
}

/** 7 → "R-007". */
export function formatRiskId(id: Maybe<number>): string {
  if (isMissing(id)) return EMPTY
  return `R-${String(id).padStart(3, '0')}`
}

/** A plain ratio such as SPI: 0.9389 → "0.94". */
export function formatRatio(value: Maybe<number>, digits = 2): string {
  if (isMissing(value)) return EMPTY
  return value.toFixed(digits)
}

/** A signed change with a real minus sign: -0.02 → "−0.02". Hides rounding to zero. */
export function formatDelta(value: Maybe<number>, digits = 2): string | undefined {
  if (isMissing(value)) return undefined
  const rounded = value.toFixed(digits)
  if (Number(rounded) === 0) return `±${Math.abs(Number(rounded)).toFixed(digits)}`
  return value > 0 ? `+${rounded}` : `−${rounded.slice(1)}`
}

/** Calendar days from `today` to `value`; negative once the date has passed. */
export function daysUntil(value: string, today = new Date()): number {
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((parseDate(value).getTime() - start.getTime()) / 86_400_000)
}

/** "25 days left", "Due today" or "3 days overdue". */
export function formatDaysLeft(days: number): string {
  if (days === 0) return 'Due today'
  const count = Math.abs(days)
  const unit = count === 1 ? 'day' : 'days'
  return days > 0 ? `${count} ${unit} left` : `${count} ${unit} overdue`
}

/** Compact axis label in lakh: 450000 → "₹4.5L". */
export function formatLakh(amount: number): string {
  return `₹${Number((amount / 100_000).toFixed(1))}L`
}

/** "Meera Iyer" → "MI". */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return EMPTY
  const first = parts[0][0]
  const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return `${first}${last}`.toUpperCase()
}
