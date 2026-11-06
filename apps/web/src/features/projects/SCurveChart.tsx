import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from 'recharts'
import { formatLakh, formatRupees, formatShortDate } from '@/lib/format'
import { type CurvePoint, dateToTime } from './metrics'
import { S_CURVE_SERIES } from './sCurveSeries'

const AXIS_TEXT = { fill: 'var(--text-subtle)', fontSize: 11, fontFamily: 'var(--font-mono)' }
const dateLabel = (time: number) => formatShortDate(new Date(time).toISOString().slice(0, 10))

function CurveTooltip({ active, payload }: TooltipContentProps) {
  const point = payload?.[0]?.payload as CurvePoint | undefined
  if (!active || !point) return null
  return (
    <div className="rounded-lg bg-surface-2 px-3 py-2 ring-1 ring-border-strong">
      <p className="micro-label">{formatShortDate(point.on)}</p>
      <dl className="mt-1 grid grid-cols-[auto_auto] gap-x-4 text-xs">
        {S_CURVE_SERIES.filter(({ key }) => point[key] !== null).map(({ key, name }) => (
          <div key={key} className="contents">
            <dt className="text-muted-foreground">{name}</dt>
            <dd className="numeric text-right">{formatRupees(point[key])}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

interface SCurveChartProps {
  points: CurvePoint[]
  today: string
  deadline: string
}

export function SCurveChart({ points, today, deadline }: SCurveChartProps) {
  return (
    <ResponsiveContainer width="100%" height={232}>
      <LineChart data={points} margin={{ top: 20, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis
          dataKey="time"
          type="number"
          scale="time"
          domain={['dataMin', 'dataMax']}
          tickFormatter={dateLabel}
          tick={AXIS_TEXT}
          tickLine={false}
          axisLine={{ stroke: 'var(--border)' }}
          minTickGap={48}
        />
        <YAxis
          tickFormatter={formatLakh}
          tick={AXIS_TEXT}
          tickLine={false}
          axisLine={false}
          width={48}
        />
        <Tooltip
          content={CurveTooltip}
          cursor={{ stroke: 'var(--border-strong)' }}
          isAnimationActive={false}
        />
        <ReferenceLine
          x={dateToTime(today)}
          stroke="var(--border-strong)"
          label={{ value: 'Today', position: 'top', ...AXIS_TEXT }}
        />
        <ReferenceLine
          x={dateToTime(deadline)}
          stroke="var(--border-strong)"
          label={{ value: 'Deadline', position: 'top', ...AXIS_TEXT }}
        />
        {S_CURVE_SERIES.map(({ key, name, colour, dash }) => (
          <Line
            key={key}
            dataKey={key}
            name={name}
            stroke={colour}
            strokeDasharray={dash}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            dot={false}
            activeDot={{ r: 4, stroke: 'var(--surface)', strokeWidth: 2 }}
            connectNulls={key === 'pv'}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
