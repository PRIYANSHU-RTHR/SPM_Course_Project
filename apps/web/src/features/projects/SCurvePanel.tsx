import { lazy, Suspense } from 'react'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRupees } from '@/lib/format'
import { sCurve } from './metrics'
import { useEvm, useProjectFull } from './queries'
import { S_CURVE_SERIES } from './sCurveSeries'

// Recharts is heavy, so it loads only on pages that draw a chart.
const SCurveChart = lazy(() =>
  import('./SCurveChart').then((module) => ({ default: module.SCurveChart })),
)

function ChartSkeleton() {
  return <Skeleton className="h-[232px] w-full" />
}

export function SCurvePanel({ projectId }: { projectId: number }) {
  const evm = useEvm(projectId)
  const full = useProjectFull(projectId)
  const data = evm.data
  const points = data ? sCurve(data) : []

  return (
    <Panel title="S-curve" className="lg:col-span-3">
      {evm.isLoading ? (
        <div className="p-4">
          <ChartSkeleton />
        </div>
      ) : evm.isError ? (
        <PanelError message={evm.error.message} onRetry={() => void evm.refetch()} />
      ) : !data || data.snapshots.length === 0 ? (
        <PanelEmpty>No progress has been recorded yet.</PanelEmpty>
      ) : (
        <div className="p-4">
          <ul className="mb-3 flex flex-wrap gap-x-5 gap-y-1">
            {S_CURVE_SERIES.map(({ key, name, colour, dash }) => (
              <li key={key} className="flex items-center gap-2 text-xs text-muted-foreground">
                <span
                  aria-hidden
                  className="w-4 border-t-2"
                  style={{ borderColor: colour, borderStyle: dash ? 'dashed' : 'solid' }}
                />
                {name}
                <span className="numeric text-foreground">{formatRupees(data[key])}</span>
              </li>
            ))}
          </ul>
          <div
            role="img"
            aria-label={`S-curve to ${data.as_of}: planned value ${formatRupees(data.pv)}, earned value ${formatRupees(data.ev)}, actual cost ${formatRupees(data.ac)}.`}
          >
            <Suspense fallback={<ChartSkeleton />}>
              <SCurveChart
                points={points}
                today={data.as_of}
                deadline={full.data?.project.deadline ?? data.as_of}
              />
            </Suspense>
          </div>
        </div>
      )}
    </Panel>
  )
}
