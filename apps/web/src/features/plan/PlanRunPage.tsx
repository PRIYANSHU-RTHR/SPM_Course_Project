import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelError } from '@/components/Panel'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/lib/api/client'
import type { PlanReview } from '@/lib/api/schemas'
import { formatProjectId } from '@/lib/format'
import { buildTimeline, type Edits, type TaskEdit } from './planModel'
import { useSkills, useWorkflowState } from './queries'
import { ReviewActions } from './ReviewActions'
import { ReviewSummary } from './ReviewSummary'
import { RunTimeline } from './RunTimeline'
import { useWorkflowEvents } from './useWorkflowEvents'
import { WbsTree } from './WbsTree'

const LINK = buttonVariants({ variant: 'outline', size: 'sm' })
const PRIMARY = buttonVariants({ size: 'sm' })

/** Keyed by revision: a re-estimated plan starts with no local edits. */
function Review({ threadId, review }: { threadId: string; review: PlanReview }) {
  const skills = useSkills()
  const [edits, setEdits] = useState<Edits>({})
  const vocabulary = (skills.data?.items ?? []).map((s) => s.name).sort()
  const onEdit = (taskId: string, edit: TaskEdit) =>
    setEdits((all) => ({ ...all, [taskId]: { ...all[taskId], ...edit } }))

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <ReviewSummary review={review} />
      <Panel title="Work breakdown">
        <WbsTree review={review} edits={edits} vocabulary={vocabulary} onEdit={onEdit} />
        <div className="border-t px-4 py-3">
          <ReviewActions
            threadId={threadId}
            review={review}
            edits={edits}
            onDiscard={() => setEdits({})}
          />
        </div>
      </Panel>
    </div>
  )
}

function Waiting({ label }: { label: string }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      <p className="text-muted-foreground">{label}</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {[0, 1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-[84px]" />
        ))}
      </div>
      <Skeleton className="h-72 w-full" />
    </div>
  )
}

export function PlanRunPage() {
  const { threadId = '' } = useParams()
  const queryClient = useQueryClient()
  const state = useWorkflowState(threadId)
  const { events, disconnected } = useWorkflowEvents(threadId)
  const run = state.data
  const status = run?.status

  useEffect(() => {
    if (status === 'committed') void queryClient.invalidateQueries({ queryKey: ['projects'] })
  }, [status, queryClient])

  if (state.error instanceof ApiError && state.error.status === 404) {
    return (
      <>
        <PageHeader label="404" title="Planning run not found" />
        <Link to="/plan/new" className={LINK}>
          Start a new plan
        </Link>
      </>
    )
  }

  return (
    <>
      <PageHeader label={`Plan run · ${threadId.slice(0, 8)}`} title={run?.review?.project_name ?? 'Planning run'}>
        {status === 'waiting'
          ? 'Review the draft. Edit hours or skills and request changes, or approve it.'
          : status === 'running'
            ? 'The workflow is running. Steps appear on the left as they finish.'
            : null}
      </PageHeader>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[272px_minmax(0,1fr)]">
        <Panel title="Run" className="self-start">
          <RunTimeline steps={buildTimeline(events)} pending={!status || status === 'running'} />
          {disconnected && status === 'running' ? (
            <p className="border-t px-4 py-2 text-xs text-warning">Live updates stopped. Reload to reconnect.</p>
          ) : null}
        </Panel>
        <div className="min-w-0">
          {state.isLoading ? (
            <Waiting label="Loading the run." />
          ) : state.isError ? (
            <Panel title="Run">
              <PanelError message={state.error.message} onRetry={() => void state.refetch()} />
            </Panel>
          ) : status === 'waiting' && run?.review ? (
            <Review key={run.review.revision} threadId={threadId} review={run.review} />
          ) : status === 'committed' && run?.project_id != null ? (
            <Panel title="Project created">
              <div className="flex flex-col items-start gap-3 p-4">
                <p>
                  <span className="font-mono">{formatProjectId(run.project_id)}</span> is saved with
                  its tasks, dependencies and recommended owners. Every assignment is in the audit log.
                </p>
                <div className="flex gap-2">
                  <Link to={`/projects/${run.project_id}`} className={PRIMARY}>
                    Open overview
                  </Link>
                  <Link to={`/projects/${run.project_id}/schedule`} className={LINK}>
                    Schedule
                  </Link>
                </div>
              </div>
            </Panel>
          ) : status === 'rejected' ? (
            <Panel title="Plan rejected">
              <div className="flex flex-col items-start gap-3 p-4">
                <p className="text-muted-foreground">Reason: {run?.reason ?? 'none given'}</p>
                <Link to="/plan/new" className={LINK}>
                  Start a new plan
                </Link>
              </div>
            </Panel>
          ) : status === 'failed' ? (
            <Panel title="Run failed">
              <div className="flex flex-col items-start gap-3 p-4">
                <p className="text-danger">{run?.error ?? 'The workflow stopped with an error.'}</p>
                <Link to="/plan/new" className={LINK}>
                  Try again
                </Link>
              </div>
            </Panel>
          ) : (
            <Waiting label="Drafting and estimating the plan." />
          )}
        </div>
      </div>
    </>
  )
}
