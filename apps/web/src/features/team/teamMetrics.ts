/** Shapes team and assignment data for display. Scores come from the assignment engine. */
import { addDays } from '@/lib/dates'
import type {
  Assignment,
  Member,
  ProjectFull,
  Recommendation,
  RecommendResponse,
  ScheduledTask,
  Score,
  Task,
  WeekLoad,
} from '@/lib/api/schemas'

const EXPERT_LEVEL = 4

export function skillNames(members: Member[]): string[] {
  return [...new Set(members.flatMap((m) => m.skills.map((s) => s.skill)))].sort()
}

export function levelOf(member: Member, skill: string): number {
  return member.skills.find((item) => item.skill === skill)?.level ?? 0
}

/** Skills with exactly one person at level 4 or above, mapped to that person's name. */
export function busFactorSkills(members: Member[]): Map<string, string> {
  const risky = new Map<string, string>()
  for (const skill of skillNames(members)) {
    const experts = members.filter((member) => levelOf(member, skill) >= EXPERT_LEVEL)
    if (experts.length === 1) risky.set(skill, experts[0].name)
  }
  return risky
}

export function weekStarts(loads: WeekLoad[]): string[] {
  return [...new Set(loads.map((load) => load.week_start))].sort()
}

export const loadKey = (memberId: number, week: string) => `${memberId}:${week}`

export function loadsByCell(loads: WeekLoad[]): Map<string, WeekLoad> {
  return new Map(loads.map((load) => [loadKey(load.member_id, load.week_start), load]))
}

/** Share of the accent colour for a utilisation, capped so text stays readable. */
export function heatShare(utilisation: number): number {
  return Math.round(Math.min(Math.max(utilisation, 0), 1) * 62)
}

/** Tasks owned by a member that overlap the week starting on `week`. */
export function weekTasks(tasks: ScheduledTask[], memberId: number, week: string): ScheduledTask[] {
  const sunday = addDays(week, 6)
  return tasks.filter(
    (task) => task.member_id === memberId && task.start <= sunday && task.end >= week,
  )
}

/** Seeded rows store `score`; engine scores use `total`. Reads either. */
export function storedScore(breakdown: Assignment['score_breakdown']): number | null {
  const value = breakdown.score ?? breakdown.total
  return typeof value === 'number' ? value : null
}

export interface AssignmentRow {
  task: Task
  assignment: Assignment | undefined
  recommendation: Recommendation | undefined
}

export function assignmentRows(
  full: ProjectFull,
  recommend: RecommendResponse | undefined,
): AssignmentRow[] {
  const current = new Map(full.assignments.map((item) => [item.task_id, item]))
  const recommended = new Map(recommend?.recommendations.map((item) => [item.task_id, item]))
  return [...full.tasks]
    .sort((a, b) => a.id - b.id)
    .map((task) => ({
      task,
      assignment: current.get(task.id),
      recommendation: recommended.get(task.id),
    }))
}

export const SCORE_PARTS = [
  { key: 'skill_part', label: 'Skill', colour: 'var(--accent)' },
  { key: 'capacity_part', label: 'Capacity', colour: 'var(--text-muted)' },
  { key: 'balance_part', label: 'Balance', colour: 'var(--warning)' },
] as const

/** Keeps both key names, so stored rows read the same as seeded ones. */
export function toBreakdown(score: Score | null | undefined): Record<string, unknown> {
  return score ? { ...score, score: score.total } : {}
}

export interface ModeComparison {
  label: string
  greedy: string
  optimal: string
  delta: number
  digits: number
}

export function compareModes(
  comparison: RecommendResponse['comparison'],
): ModeComparison[] {
  const rows = [
    ['Total score', comparison.greedy_total, comparison.optimal_total, 0],
    ['Utilisation std-dev', comparison.greedy_utilisation_std, comparison.optimal_utilisation_std, 2],
    ['Unassigned', comparison.greedy_unassigned, comparison.optimal_unassigned, 0],
  ] as const
  return rows.map(([label, greedy, optimal, digits]) => ({
    label,
    greedy: greedy.toLocaleString('en-IN', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
    optimal: optimal.toLocaleString('en-IN', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
    delta: optimal - greedy,
    digits,
  }))
}
