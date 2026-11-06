import { Link } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { TableCell, TableRow } from '@/components/ui/table'
import type { Project } from '@/lib/api/schemas'
import {
  formatDate,
  formatDaysLeft,
  daysUntil,
  formatPercent,
  formatProjectId,
  formatRatio,
} from '@/lib/format'
import { hasPlan, openRisks, progress } from './metrics'
import { useEvm, useForecast, useRisks } from './queries'

function ProgressBar({ value }: { value: number | null }) {
  if (value === null) return <span className="numeric text-subtle">—</span>
  return (
    <div className="flex items-center gap-2">
      <div
        role="progressbar"
        aria-label="Progress"
        aria-valuenow={Math.round(value * 100)}
        className="h-1.5 w-24 overflow-hidden rounded-sm bg-surface-2"
      >
        <div className="h-full bg-brand" style={{ width: `${value * 100}%` }} />
      </div>
      <span className="numeric text-muted-foreground">{formatPercent(value)}</span>
    </div>
  )
}

export function ProjectRow({ project }: { project: Project }) {
  const forecast = useForecast(project.id)
  const evm = useEvm(project.id)
  const risks = useRisks(project.id)
  const planned = evm.data ? hasPlan(evm.data) : false
  const metric = (isLoading: boolean, value: string) =>
    isLoading ? <Skeleton className="ml-auto h-4 w-10" /> : value

  return (
    <TableRow>
      <TableCell className="numeric text-muted-foreground">
        {formatProjectId(project.id)}
      </TableCell>
      <TableCell>
        <Link
          to={`/projects/${project.id}`}
          className="rounded-sm font-medium underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {project.name}
        </Link>
      </TableCell>
      <TableCell>
        <span className="numeric">{formatDate(project.deadline)}</span>
        <span className="ml-2 text-muted-foreground">
          {formatDaysLeft(daysUntil(project.deadline))}
        </span>
      </TableCell>
      <TableCell>
        {evm.isLoading ? (
          <Skeleton className="h-4 w-32" />
        ) : (
          <ProgressBar value={evm.data ? progress(evm.data) : null} />
        )}
      </TableCell>
      <TableCell className="numeric text-right">
        {metric(forecast.isLoading || evm.isLoading, planned ? formatPercent(forecast.data?.p_on_time) : '—')}
      </TableCell>
      <TableCell className="numeric text-right">
        {metric(evm.isLoading, formatRatio(evm.data?.spi))}
      </TableCell>
      <TableCell className="numeric text-right">
        {metric(risks.isLoading, risks.data ? String(openRisks(risks.data.items).length) : '—')}
      </TableCell>
    </TableRow>
  )
}
