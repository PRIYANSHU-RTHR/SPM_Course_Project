import { lazy, Suspense } from 'react'
import { AnimatedNumber } from '@/components/AnimatedNumber'
import { Panel, PanelError } from '@/components/Panel'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { forecastStatus } from '@/features/projects/metrics'
import { useForecast, useProjectFull } from '@/features/projects/queries'
import { formatDate, formatPercent, formatTaskId } from '@/lib/format'
import { cn } from '@/lib/utils'
import { percentileMarks, topCriticality } from './forecastData'

const FinishHistogram = lazy(() =>
  import('./ForecastCharts').then((module) => ({ default: module.FinishHistogram })),
)
const CompletionCdf = lazy(() =>
  import('./ForecastCharts').then((module) => ({ default: module.CompletionCdf })),
)

const CHART_SKELETON = <Skeleton className="h-[216px] w-full" />
const STATUS_TEXT = { warning: 'text-warning', danger: 'text-danger' } as const
const percent = (value: number) => formatPercent(value)

export function ForecastSection({ projectId }: { projectId: number }) {
  const forecast = useForecast(projectId)
  const full = useProjectFull(projectId)
  const data = forecast.data
  const start = full.data?.project.start_date

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-[15px] leading-5 font-semibold">Forecast</h2>
      {forecast.isError ? (
        <div className="rounded-xl border bg-surface">
          <PanelError message={forecast.error.message} onRetry={() => void forecast.refetch()} />
        </div>
      ) : !data || !start ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-6">
          <Panel title="P(on time)" className="lg:col-span-2">
            <div className="flex flex-1 flex-col justify-between gap-4 p-4">
              <div>
                <p
                  className={cn(
                    'numeric text-5xl leading-none',
                    forecastStatus(data.p_on_time) && STATUS_TEXT[forecastStatus(data.p_on_time)!],
                  )}
                >
                  <AnimatedNumber value={data.p_on_time} format={percent} />
                </p>
                <p className="mt-2 text-muted-foreground">
                  By <span className="numeric">{formatDate(data.deadline)}</span>
                </p>
              </div>
              <dl className="flex flex-col gap-1">
                {percentileMarks(data).map(({ label, date }) => (
                  <div key={label} className="flex justify-between gap-3">
                    <dt className="micro-label">{label}</dt>
                    <dd className="numeric">{formatDate(date)}</dd>
                  </div>
                ))}
              </dl>
              <p className="micro-label">{data.runs.toLocaleString('en-IN')} runs</p>
            </div>
          </Panel>
          <Panel title="Finish dates" className="lg:col-span-4">
            <div className="p-4">
              <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <li className="flex items-center gap-2">
                  <span aria-hidden className="size-2.5 rounded-sm bg-brand" />
                  On time
                </li>
                <li className="flex items-center gap-2">
                  <span aria-hidden className="size-2.5 rounded-sm bg-subtle" />
                  After the deadline
                </li>
              </ul>
              <div
                role="img"
                aria-label={`Histogram of ${data.runs} simulated finish dates. ${formatPercent(data.p_on_time)} finish by the deadline.`}
              >
                <Suspense fallback={CHART_SKELETON}>
                  <FinishHistogram forecast={data} start={start} />
                </Suspense>
              </div>
            </div>
          </Panel>
          <Panel title="Chance of finishing by each date" className="lg:col-span-3">
            <div
              className="p-4"
              role="img"
              aria-label={`Cumulative chance of finishing. P50 ${data.p50.on}, P80 ${data.p80.on}, P95 ${data.p95.on}.`}
            >
              <Suspense fallback={CHART_SKELETON}>
                <CompletionCdf forecast={data} start={start} />
              </Suspense>
            </div>
          </Panel>
          <Panel title="Highest criticality" className="lg:col-span-3">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">ID</TableHead>
                  <TableHead>Task</TableHead>
                  <TableHead className="text-right">Index</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topCriticality(data, full.data?.tasks ?? []).map(({ task, index }) => (
                  <TableRow key={task.id}>
                    <TableCell className="numeric text-muted-foreground">
                      {formatTaskId(task.id)}
                    </TableCell>
                    <TableCell>{task.title}</TableCell>
                    <TableCell className="numeric text-right">{formatPercent(index)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Panel>
        </div>
      )}
    </section>
  )
}
