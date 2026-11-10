import { memo } from 'react'
import { formatDate, formatHours, formatTaskId } from '@/lib/format'
import { ownerColour } from '@/lib/tokens'
import type { PlanTask } from './plan'
import { ROW_HEIGHT } from './timeline'

const BAR_HEIGHT = 16
const HATCH =
  'repeating-linear-gradient(135deg, var(--border-strong) 0 2px, transparent 2px 5px)'

interface GanttBarProps {
  task: PlanTask
  row: number
  left: number
  width: number
  tail: number
  onHover: (taskId: number | null) => void
  onSelect: (taskId: number) => void
}

export const GanttBar = memo(function GanttBar({
  task,
  row,
  left,
  width,
  tail,
  onHover,
  onSelect,
}: GanttBarProps) {
  const top = row * ROW_HEIGHT + (ROW_HEIGHT - BAR_HEIGHT) / 2
  const colour = task.ownerId === undefined ? 'var(--text-subtle)' : ownerColour(task.ownerId)
  const label = [
    formatTaskId(task.id),
    task.title,
    `${formatDate(task.start)} to ${formatDate(task.end)}`,
    `${formatHours(task.hours)} expected`,
    task.ownerName ?? 'Unassigned',
    task.critical ? 'Critical' : `${formatHours(task.totalSlack)} slack`,
  ].join(', ')

  return (
    <>
      {tail > 0 ? (
        <span
          aria-hidden
          className="pointer-events-none absolute rounded-r-sm"
          style={{ left: left + width, top, width: tail, height: BAR_HEIGHT, background: HATCH }}
        />
      ) : null}
      <button
        type="button"
        aria-label={label}
        title={label}
        onMouseEnter={() => onHover(task.id)}
        onMouseLeave={() => onHover(null)}
        onFocus={() => onHover(task.id)}
        onBlur={() => onHover(null)}
        onClick={() => onSelect(task.id)}
        className="absolute cursor-pointer rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        style={{
          left,
          top,
          width,
          height: BAR_HEIGHT,
          background: colour,
          borderLeft: task.critical ? '3px solid var(--accent)' : undefined,
          // A surface gap keeps the edge visible on bars in a similar blue.
          boxShadow: task.critical ? 'inset 2px 0 0 var(--surface)' : undefined,
        }}
      />
    </>
  )
})
