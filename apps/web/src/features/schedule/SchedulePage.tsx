import { TriangleAlert } from 'lucide-react'
import { lazy, Suspense, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCpm, useMembers, useProjectFull, useSchedule } from '@/features/projects/queries'
import { ApiError } from '@/lib/api/client'
import { workingDaysBetween } from '@/lib/dates'
import { formatDate } from '@/lib/format'
import { GanttView } from './GanttView'
import { buildPlan } from './plan'
import { TaskSheet } from './TaskSheet'

// React Flow and the layout library load only when the Network tab opens.
const NetworkView = lazy(() =>
  import('./NetworkView').then((module) => ({ default: module.NetworkView })),
)

const LINK_BUTTON = buttonVariants({ variant: 'outline', size: 'sm' })
const CANVAS_SKELETON = <Skeleton className="h-[480px] w-full md:h-[600px]" />

function FinishNote({ finish, deadline }: { finish: string; deadline: string }) {
  const late = workingDaysBetween(deadline, finish)
  return (
    <>
      Finish <span className="numeric whitespace-nowrap text-foreground">{formatDate(finish)}</span>
      <span className="mx-2 text-subtle">·</span>
      Deadline <span className="numeric whitespace-nowrap text-foreground">{formatDate(deadline)}</span>
      {late > 0 ? (
        <span className="mt-1 flex items-center gap-1.5 text-warning sm:ml-3 sm:mt-0 sm:inline-flex">
          <TriangleAlert className="size-3.5" strokeWidth={1.5} aria-hidden />
          {late} working {late === 1 ? 'day' : 'days'} after the deadline
        </span>
      ) : null}
    </>
  )
}

export function SchedulePage() {
  const { projectId: param } = useParams()
  const parsed = Number(param)
  const projectId = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
  const full = useProjectFull(projectId)
  const cpm = useCpm(projectId)
  const schedule = useSchedule(projectId)
  const members = useMembers()
  const [selected, setSelected] = useState<number | null>(null)

  const plan = useMemo(
    () =>
      full.data && cpm.data && schedule.data
        ? buildPlan(full.data, cpm.data, schedule.data, members.data?.items ?? [])
        : undefined,
    [full.data, cpm.data, schedule.data, members.data],
  )

  const failed = full.error ?? cpm.error ?? schedule.error
  if (projectId === undefined || (failed instanceof ApiError && failed.status === 404)) {
    return (
      <>
        <PageHeader label="404" title="Project not found" />
        <Link to="/projects" className={LINK_BUTTON}>
          All projects
        </Link>
      </>
    )
  }

  if (failed) {
    return (
      <>
        <PageHeader label="Schedule" title="Schedule" />
        <Panel title="Schedule">
          <PanelError
            message={failed.message}
            onRetry={() => {
              void full.refetch()
              void cpm.refetch()
              void schedule.refetch()
            }}
          />
        </Panel>
      </>
    )
  }

  if (!plan || !full.data) {
    return (
      <>
        <PageHeader label="Schedule" title="Schedule" />
        {CANVAS_SKELETON}
      </>
    )
  }

  if (plan.tasks.length === 0) {
    return (
      <>
        <PageHeader label="Schedule" title={full.data.project.name} />
        <Panel title="Schedule">
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
      </>
    )
  }

  return (
    <>
      <PageHeader label="Schedule" title={full.data.project.name}>
        <FinishNote finish={plan.finish} deadline={plan.deadline} />
      </PageHeader>
      <Tabs defaultValue="network">
        <TabsList>
          <TabsTrigger value="network">Network</TabsTrigger>
          <TabsTrigger value="gantt">Gantt</TabsTrigger>
        </TabsList>
        <TabsContent value="network" className="mt-3">
          <Suspense fallback={CANVAS_SKELETON}>
            <NetworkView plan={plan} onSelect={setSelected} />
          </Suspense>
        </TabsContent>
        <TabsContent value="gantt" className="mt-3 min-w-0">
          <GanttView plan={plan} onSelect={setSelected} />
        </TabsContent>
      </Tabs>
      <TaskSheet
        plan={plan}
        task={selected === null ? undefined : plan.byId.get(selected)}
        onSelect={setSelected}
        onClose={() => setSelected(null)}
      />
    </>
  )
}
