import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { OwnerChip } from '@/components/OwnerChip'
import { Button } from '@/components/ui/button'
import { todayIso } from '@/lib/dates'
import { formatTaskId } from '@/lib/format'
import { cn } from '@/lib/utils'
import { AXIS_HEIGHT, GanttAxis } from './GanttAxis'
import { GanttBar } from './GanttBar'
import type { Plan } from './plan'
import {
  barSpan,
  buildRows,
  buildTimeline,
  DAY_WIDTH,
  dayX,
  dependencyPath,
  ROW_HEIGHT,
  type Zoom,
} from './timeline'

const LEFT_COLUMN = 'w-36 md:w-72'

interface GanttViewProps {
  plan: Plan
  onSelect: (taskId: number) => void
}

export function GanttView({ plan, onSelect }: GanttViewProps) {
  const [zoom, setZoom] = useState<Zoom>('day')
  const [hovered, setHovered] = useState<number | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const today = todayIso()
  const timeline = useMemo(() => buildTimeline(plan, today), [plan, today])
  const rows = useMemo(() => buildRows(plan), [plan])
  const rowOf = useMemo(
    () =>
      new Map(rows.flatMap((row, index) => (row.kind === 'task' ? [[row.task.id, index]] : []))),
    [rows],
  )
  const width = timeline.days.length * DAY_WIDTH[zoom]
  const height = rows.length * ROW_HEIGHT
  const onHover = useCallback((taskId: number | null) => setHovered(taskId), [])

  useEffect(() => {
    const element = scroller.current
    if (element) element.scrollLeft = Math.max(dayX(timeline, today, zoom) - 160, 0)
  }, [timeline, today, zoom])

  const lines = useMemo(() => {
    const task = hovered === null ? undefined : plan.byId.get(hovered)
    if (!task) return []
    const endX = (id: number) => {
      const other = plan.byId.get(id)!
      const span = barSpan(timeline, other, zoom)
      return { x: span.left + span.width, row: rowOf.get(id)! }
    }
    const startX = (id: number) => ({
      x: barSpan(timeline, plan.byId.get(id)!, zoom).left,
      row: rowOf.get(id)!,
    })
    return [
      ...task.predecessors.map((id) => dependencyPath(endX(id), startX(task.id))),
      ...task.successors.map((id) => dependencyPath(endX(task.id), startX(id))),
    ]
  }, [hovered, plan, rowOf, timeline, zoom])

  return (
    <div className="min-w-0 rounded-xl border bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-2">
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <li className="flex items-center gap-2">
            <span aria-hidden className="h-3 w-1 bg-brand" />
            Critical
          </li>
          <li className="flex items-center gap-2">
            <span
              aria-hidden
              className="h-3 w-5"
              style={{
                background:
                  'repeating-linear-gradient(135deg, var(--border-strong) 0 2px, transparent 2px 5px)',
              }}
            />
            Slack
          </li>
          <li>Bars use each owner&apos;s colour</li>
        </ul>
        <div role="group" aria-label="Zoom" className="flex gap-1">
          {(['day', 'week'] as const).map((level) => (
            <Button
              key={level}
              variant={zoom === level ? 'secondary' : 'ghost'}
              size="sm"
              aria-pressed={zoom === level}
              onClick={() => setZoom(level)}
            >
              {level === 'day' ? 'Day' : 'Week'}
            </Button>
          ))}
        </div>
      </div>

      <div ref={scroller} className="flex max-h-[640px] overflow-auto">
        <div className={cn('sticky left-0 z-20 shrink-0 border-r bg-surface', LEFT_COLUMN)}>
          <div
            className="micro-label sticky top-0 z-10 flex items-end border-b bg-surface-2 px-3 pb-2"
            style={{ height: AXIS_HEIGHT }}
          >
            Task
          </div>
          {rows.map((row) =>
            row.kind === 'epic' ? (
              <div
                key={row.key}
                className="micro-label flex items-center truncate bg-surface-2/50 px-3"
                style={{ height: ROW_HEIGHT }}
              >
                {row.title}
              </div>
            ) : (
              <div
                key={row.key}
                className={cn(
                  'flex items-center gap-2 px-3',
                  hovered === row.task.id && 'bg-surface-2',
                )}
                style={{ height: ROW_HEIGHT }}
              >
                <span className="numeric shrink-0 text-xs text-muted-foreground">
                  {formatTaskId(row.task.id)}
                </span>
                <span className="min-w-0 flex-1 truncate text-[13px]">{row.task.title}</span>
                {row.task.ownerId !== undefined && row.task.ownerName ? (
                  <span className="hidden md:inline-flex">
                    <OwnerChip id={row.task.ownerId} name={row.task.ownerName} />
                  </span>
                ) : null}
              </div>
            ),
          )}
        </div>

        <div className="relative flex-1" style={{ minWidth: width }}>
          <GanttAxis timeline={timeline} zoom={zoom} today={today} deadline={plan.deadline} />
          <div className="relative" style={{ height }}>
            {timeline.weekends.map((day) => (
              <span
                key={day}
                aria-hidden
                className="absolute top-0 bottom-0 bg-surface-2/60"
                style={{ left: dayX(timeline, day, zoom), width: DAY_WIDTH[zoom] }}
              />
            ))}
            {rows.map((row, index) =>
              row.kind === 'epic' ? (
                <span
                  key={row.key}
                  aria-hidden
                  className="absolute right-0 left-0 bg-surface-2/50"
                  style={{ top: index * ROW_HEIGHT, height: ROW_HEIGHT }}
                />
              ) : null,
            )}
            <span
              aria-hidden
              className="absolute top-0 bottom-0 w-px bg-foreground/60"
              style={{ left: dayX(timeline, today, zoom) }}
            />
            <span
              aria-hidden
              className="absolute top-0 bottom-0 w-px bg-warning"
              style={{ left: dayX(timeline, plan.deadline, zoom) }}
            />
            {rows.map((row, index) => {
              if (row.kind !== 'task') return null
              const span = barSpan(timeline, row.task, zoom)
              return (
                <GanttBar
                  key={row.key}
                  task={row.task}
                  row={index}
                  left={span.left}
                  width={span.width}
                  tail={span.tail}
                  onHover={onHover}
                  onSelect={onSelect}
                />
              )
            })}
            {lines.length > 0 ? (
              <svg
                aria-hidden
                className="pointer-events-none absolute inset-0 z-10"
                width={width}
                height={height}
              >
                {lines.map((path) => (
                  <path key={path} d={path} fill="none" stroke="var(--accent)" strokeWidth={1.5} />
                ))}
              </svg>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
