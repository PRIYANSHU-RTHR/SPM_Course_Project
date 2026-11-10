import { Link, useParams } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useMembers, useProjectFull, useSchedule } from '@/features/projects/queries'
import { ApiError } from '@/lib/api/client'
import { AssignmentsPanel } from './AssignmentsPanel'
import { CapacityHeatmap } from './CapacityHeatmap'
import { SkillsMatrix } from './SkillsMatrix'

const LINK_BUTTON = buttonVariants({ variant: 'outline', size: 'sm' })

export function TeamPage() {
  const { projectId: param } = useParams()
  const parsed = Number(param)
  const projectId = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
  const full = useProjectFull(projectId)
  const members = useMembers()
  const schedule = useSchedule(projectId)
  const failed = full.error ?? members.error ?? schedule.error

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

  const title = full.data?.project.name ?? 'Team'

  if (failed) {
    return (
      <>
        <PageHeader label="Team" title={title} />
        <Panel title="Team">
          <PanelError
            message={failed.message}
            onRetry={() => {
              void full.refetch()
              void members.refetch()
              void schedule.refetch()
            }}
          />
        </Panel>
      </>
    )
  }

  if (!full.data || !members.data || !schedule.data) {
    return (
      <>
        <PageHeader label="Team" title={title} />
        <div className="flex flex-col gap-3">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      </>
    )
  }

  const team = members.data.items

  return (
    <>
      <PageHeader label="Team" title={title} />
      <div className="flex flex-col gap-3">
        <SkillsMatrix members={team} />
        {full.data.tasks.length === 0 ? (
          <Panel title="Assignments">
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
          <>
            <CapacityHeatmap members={team} schedule={schedule.data} full={full.data} />
            <AssignmentsPanel full={full.data} members={team} />
          </>
        )}
      </div>
    </>
  )
}
