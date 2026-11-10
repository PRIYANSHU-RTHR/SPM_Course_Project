/** Calendar maths on ISO date strings ("2026-12-01"). Uses UTC, so time zones cannot shift a day. */

const DAY_MS = 86_400_000
const HOURS_PER_DAY = 8 // one project day of effort, matching the engines' calendar

function toTime(date: string): number {
  return new Date(`${date}T00:00:00Z`).getTime()
}

export function addDays(date: string, days: number): string {
  return new Date(toTime(date) + days * DAY_MS).toISOString().slice(0, 10)
}

export function daysBetween(from: string, to: string): number {
  return Math.round((toTime(to) - toTime(from)) / DAY_MS)
}

export function isWeekend(date: string): boolean {
  const day = new Date(toTime(date)).getUTCDay()
  return day === 0 || day === 6
}

export function isMonday(date: string): boolean {
  return new Date(toTime(date)).getUTCDay() === 1
}

/** ISO 8601 week number: weeks start on Monday, and week 1 holds the first Thursday. */
export function isoWeek(date: string): number {
  const day = new Date(toTime(date))
  const weekday = day.getUTCDay() || 7
  const thursday = toTime(addDays(date, 4 - weekday))
  const yearStart = Date.UTC(new Date(thursday).getUTCFullYear(), 0, 1)
  return Math.ceil(((thursday - yearStart) / DAY_MS + 1) / 7)
}

/** Today's date on the viewer's clock. */
export function todayIso(now = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

/** Working days after `from`, up to and including `to`. Negative when `to` is earlier. */
export function workingDaysBetween(from: string, to: string): number {
  const step = from <= to ? 1 : -1
  let count = 0
  for (let day = from; day !== to; ) {
    day = addDays(day, step)
    if (!isWeekend(day)) count += step
  }
  return count
}

/** The date `days` working days after `date`. */
export function addWorkingDays(date: string, days: number): string {
  let day = date
  for (let left = days; left > 0; ) {
    day = addDays(day, 1)
    if (!isWeekend(day)) left -= 1
  }
  return day
}

/** The day a task finishes when it ends `hours` of project time after `start`. */
export function dateAfterHours(start: string, hours: number): string {
  return addWorkingDays(start, Math.max(Math.ceil(hours / HOURS_PER_DAY - 1e-9) - 1, 0))
}

/** Hours of slack as whole project days, rounded up so any slack is visible. */
export function slackDays(hours: number): number {
  return Math.max(0, Math.ceil(hours / HOURS_PER_DAY - 1e-9))
}
