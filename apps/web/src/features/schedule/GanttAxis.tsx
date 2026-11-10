import { formatShortDate } from '@/lib/format'
import { dayX, type Timeline, type Zoom } from './timeline'

interface GanttAxisProps {
  timeline: Timeline
  zoom: Zoom
  today: string
  deadline: string
}

export const AXIS_HEIGHT = 44

function Marker({ x, label, className }: { x: number; label: string; className: string }) {
  return (
    <span
      className={`micro-label absolute top-0 -translate-x-1/2 bg-surface-2 px-1 leading-4 ${className}`}
      style={{ left: x }}
    >
      {label}
    </span>
  )
}

export function GanttAxis({ timeline, zoom, today, deadline }: GanttAxisProps) {
  return (
    <div className="sticky top-0 z-10 border-b bg-surface-2" style={{ height: AXIS_HEIGHT }}>
      <Marker x={dayX(timeline, today, zoom)} label="Today" className="z-10 !text-foreground" />
      <Marker x={dayX(timeline, deadline, zoom)} label="Deadline" className="z-10 !text-warning" />
      {timeline.mondays.map((monday) => (
        <span
          key={monday}
          className="numeric absolute top-4 text-[11px] leading-4 whitespace-nowrap text-muted-foreground"
          style={{ left: dayX(timeline, monday, zoom) + 2 }}
        >
          {formatShortDate(monday)}
        </span>
      ))}
    </div>
  )
}
