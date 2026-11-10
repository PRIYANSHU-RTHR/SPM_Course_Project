import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from 'recharts'
import type { ProjectForecast } from '@/lib/api/schemas'
import { formatPercent, formatShortDate } from '@/lib/format'
import { axisTicks, histogramBars, hoursToDate, percentileMarks } from './forecastData'

const AXIS_TEXT = { fill: 'var(--text-subtle)', fontSize: 11, fontFamily: 'var(--font-mono)' }
const LABEL_TEXT = { fill: 'var(--text)', fontSize: 11, fontFamily: 'var(--font-mono)' }
const HEIGHT = 216

interface ChartProps {
  forecast: ProjectForecast
  start: string
}

function TooltipBox({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg bg-surface-2 px-3 py-2 text-xs ring-1 ring-border-strong">
      <p className="micro-label">{title}</p>
      {lines.map((line) => (
        <p key={line} className="numeric mt-0.5">
          {line}
        </p>
      ))}
    </div>
  )
}

function hoursAxis(start: string, min: number, max: number) {
  return {
    type: 'number' as const,
    domain: [min, max],
    ticks: axisTicks(min, max),
    tickFormatter: (hours: number) => formatShortDate(hoursToDate(start, hours)),
    tick: AXIS_TEXT,
    tickLine: false,
    axisLine: { stroke: 'var(--border)' },
    minTickGap: 24,
  }
}

const deadlineLine = (hours: number) => (
  <ReferenceLine
    x={hours}
    stroke="var(--warning)"
    label={{ value: 'Deadline', position: 'top', ...AXIS_TEXT }}
  />
)

export function FinishHistogram({ forecast, start }: ChartProps) {
  const bars = histogramBars(forecast)
  const min = bars[0].start
  const max = bars[bars.length - 1].end

  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <BarChart data={bars} margin={{ top: 20, right: 12, bottom: 0, left: 0 }} barCategoryGap={1}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="mid" {...hoursAxis(start, min, max)} />
        <YAxis tick={AXIS_TEXT} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          cursor={{ fill: 'var(--surface-2)' }}
          isAnimationActive={false}
          content={({ active, payload }: TooltipContentProps) => {
            const bar = payload?.[0]?.payload as (typeof bars)[number] | undefined
            if (!active || !bar) return null
            return (
              <TooltipBox
                title={formatShortDate(hoursToDate(start, bar.mid))}
                lines={[`${bar.runs} runs`, bar.onTime ? 'On time' : 'After the deadline']}
              />
            )
          }}
        />
        <Bar dataKey="runs" radius={[2, 2, 0, 0]} isAnimationActive={false}>
          {bars.map((bar) => (
            <Cell key={bar.mid} fill={bar.onTime ? 'var(--accent)' : 'var(--text-subtle)'} />
          ))}
        </Bar>
        {deadlineLine(forecast.deadline_hours)}
      </BarChart>
    </ResponsiveContainer>
  )
}

export function CompletionCdf({ forecast, start }: ChartProps) {
  const points = forecast.cdf
  const min = points[0].hours
  const max = points[points.length - 1].hours

  return (
    <ResponsiveContainer width="100%" height={HEIGHT}>
      <LineChart data={points} margin={{ top: 20, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="hours" {...hoursAxis(start, min, max)} />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 0.5, 1]}
          tickFormatter={(value: number) => formatPercent(value)}
          tick={AXIS_TEXT}
          tickLine={false}
          axisLine={false}
          width={40}
        />
        <Tooltip
          cursor={{ stroke: 'var(--border-strong)' }}
          isAnimationActive={false}
          content={({ active, payload }: TooltipContentProps) => {
            const point = payload?.[0]?.payload as (typeof points)[number] | undefined
            if (!active || !point) return null
            return (
              <TooltipBox
                title={`By ${formatShortDate(hoursToDate(start, point.hours))}`}
                lines={[`${formatPercent(point.probability)} of runs finished`]}
              />
            )
          }}
        />
        {deadlineLine(forecast.deadline_hours)}
        <Line
          dataKey="probability"
          stroke="var(--accent)"
          strokeWidth={2}
          strokeLinecap="round"
          dot={false}
          activeDot={{ r: 4, stroke: 'var(--surface)', strokeWidth: 2 }}
          isAnimationActive={false}
        />
        {percentileMarks(forecast).map(({ label, probability, hours }) => (
          <ReferenceDot
            key={label}
            x={hours}
            y={probability}
            r={4}
            fill="var(--accent)"
            stroke="var(--surface)"
            strokeWidth={2}
            label={{ value: label, position: 'left', offset: 8, ...LABEL_TEXT }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
