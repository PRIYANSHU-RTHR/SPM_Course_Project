import { Link, useParams } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useProjectFull } from '@/features/projects/queries'
import { ApiError } from '@/lib/api/client'
import { EvmSection } from './EvmSection'
import { ForecastSection } from './ForecastSection'

const LINK_BUTTON = buttonVariants({ variant: 'outline', size: 'sm' })

export function ControlPage() {
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

  const title = full.data?.project.name ?? 'Monitoring and control'

  return (
    <>
      <PageHeader label="Control" title={title} />
      {full.isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : full.isError ? (
        <Panel title="Control">
          <PanelError message={full.error.message} onRetry={() => void full.refetch()} />
        </Panel>
      ) : full.data?.tasks.length === 0 ? (
        // Engines report 100% on time for an empty plan, so no metrics are shown until tasks exist.
        <Panel title="Control">
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
        <div className="flex flex-col gap-8">
          <EvmSection projectId={projectId} />
          <ForecastSection projectId={projectId} />
        </div>
      )}
    </>
  )
}
