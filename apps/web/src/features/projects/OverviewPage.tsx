import { Link, useParams } from 'react-router'
import { KpiStatSkeleton } from '@/components/KpiStat'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/lib/api/client'
import { daysUntil, formatDate, formatDaysLeft, formatProjectId } from '@/lib/format'
import { CriticalTasksPanel } from './CriticalTasksPanel'
import { KpiStrip } from './KpiStrip'
import { useProjectFull } from './queries'
import { SCurvePanel } from './SCurvePanel'
import { TopRisksPanel } from './TopRisksPanel'

const LINK_BUTTON = buttonVariants({ variant: 'outline', size: 'sm' })

function OverviewSkeleton() {
  return (
    <>
      <Skeleton className="mb-1 h-4 w-14" />
      <Skeleton className="mb-1 h-8 w-72" />
      <Skeleton className="mb-6 h-5 w-52" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {[0, 1, 2, 3, 4, 5].map((item) => (
          <KpiStatSkeleton key={item} />
        ))}
      </div>
    </>
  )
}

export function OverviewPage() {
  const { projectId: param } = useParams()
  const parsed = Number(param)
  const projectId = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
  const full = useProjectFull(projectId)

  if (projectId === undefined || (full.error instanceof ApiError && full.error.status === 404)) {
    return (
      <>
        <PageHeader label="404" title="Project not found" />
        <Link to="/projects" className={LINK_BUTTON}>
          All projects
        </Link>
      </>
    )
  }
  if (full.isLoading) return <OverviewSkeleton />
  if (full.isError || !full.data) {
    return (
      <>
        <PageHeader label={formatProjectId(projectId)} title="Project overview" />
        <Panel title="Overview">
          <PanelError
            message={full.error?.message ?? 'Could not load this project.'}
            onRetry={() => void full.refetch()}
          />
        </Panel>
      </>
    )
  }

  const { project, tasks } = full.data

  return (
    <>
      <PageHeader label={formatProjectId(project.id)} title={project.name}>
        Deadline <span className="numeric text-foreground">{formatDate(project.deadline)}</span>
        <span className="mx-2 text-subtle">·</span>
        {formatDaysLeft(daysUntil(project.deadline))}
      </PageHeader>
      {tasks.length === 0 ? (
        // Engines report 100% on time for an empty plan, so no metrics are shown until tasks exist.
        <Panel title="Overview">
          <PanelEmpty
            action={
              <Link to="/plan/new" className={LINK_BUTTON}>
                Plan this project
              </Link>
            }
          >
            This project has no tasks yet.
          </PanelEmpty>
        </Panel>
      ) : (
        <div className="flex flex-col gap-3">
          <KpiStrip projectId={project.id} />
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-6">
            <SCurvePanel projectId={project.id} />
            <TopRisksPanel projectId={project.id} />
            <div className="lg:col-span-6">
              <CriticalTasksPanel projectId={project.id} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
