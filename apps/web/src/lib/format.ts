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
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
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

/** "Meera Iyer" → "MI". */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return EMPTY
  const first = parts[0][0]
  const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return `${first}${last}`.toUpperCase()
}
