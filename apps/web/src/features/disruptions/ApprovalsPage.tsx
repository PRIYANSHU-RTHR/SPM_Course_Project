import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { Skeleton } from '@/components/ui/skeleton'
import { buildTimeline, lastStatus } from '@/features/plan/planModel'
import { RunTimeline } from '@/features/plan/RunTimeline'
import { useWorkflowEvents } from '@/features/plan/useWorkflowEvents'
import { useMembers, useProjectFull } from '@/features/projects/queries'
import { useCurrentProject } from '@/features/projects/useCurrentProject'
import type { Proposal, ProposalPayload } from '@/lib/api/schemas'
import { formatDate, formatProjectId } from '@/lib/format'
import { MetricsStrip } from './MetricsStrip'
import { ProposalCard } from './ProposalCard'
import { useMetrics, useProposals } from './queries'
import { describeDisruption, taskLabel } from './reallocModel'
import { SimulatorPanel } from './SimulatorPanel'

const STATUS_TONE: Record<Proposal['status'], string> = {
  pending: 'text-warning',
  approved: 'text-success',
  rejected: 'text-muted-foreground',
  failed: 'text-danger',
}

export function ApprovalsPage() {
  const { project, projectId, isLoading } = useCurrentProject()
  const queryClient = useQueryClient()
  const metrics = useMetrics(projectId)
  const proposals = useProposals(projectId)
  const full = useProjectFull(projectId)
  const members = useMembers()
  const [threadId, setThreadId] = useState<string>()
  const { events } = useWorkflowEvents(threadId, () =>
    queryClient.invalidateQueries({ queryKey: ['projects', projectId] }),
  )

  if (isLoading) return <Skeleton className="h-8 w-72" />
  if (!project || projectId === undefined) {
    return (
      <>
        <PageHeader label="Approvals" title="No project yet" />
        <PanelEmpty
          action={
            <Link to="/plan/new" className="text-brand">
              Plan a project
            </Link>
          }
        >
          Approvals belong to a project.
        </PanelEmpty>
      </>
    )
  }

  const titles = new Map(full.data?.tasks.map((t) => [t.id, t.title]))
  const names = {
    member: (id: number) => members.data?.items.find((m) => m.id === id)?.name ?? `Member ${id}`,
    task: (id: number) => taskLabel(id, titles.get(id)),
  }
  const items = proposals.data?.items ?? []
  const pending = items.filter(
    (p): p is Proposal & { payload: ProposalPayload } =>
      p.status === 'pending' && p.payload !== null,
  )
  const decided = items.filter((p) => p.status !== 'pending')
  const running = threadId !== undefined && lastStatus(events) === 'running'

  return (
    <>
      <PageHeader label={`Approvals · ${formatProjectId(projectId)}`} title={project.name}>
        Simulate a disruption, then approve or reject the reassignment the engines propose.
      </PageHeader>
      <div className="flex flex-col gap-3">
        <MetricsStrip projectId={projectId} />
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)]">
          <div className="flex min-w-0 flex-col gap-3">
            {metrics.data ? (
              <SimulatorPanel
                projectId={projectId}
                today={metrics.data.as_of}
                blocked={pending.length > 0 || running}
                onStarted={setThreadId}
              />
            ) : (
              <Skeleton className="h-80 w-full" />
            )}
            {threadId ? (
              <Panel title="Reallocation run">
                <RunTimeline steps={buildTimeline(events)} pending />
              </Panel>
            ) : null}
          </div>
          <div className="flex min-w-0 flex-col gap-3">
            {proposals.isLoading ? (
              <Skeleton className="h-96 w-full" />
            ) : proposals.isError ? (
              <Panel title="Inbox">
                <PanelError
                  message={proposals.error.message}
                  onRetry={() => void proposals.refetch()}
                />
              </Panel>
            ) : pending.length === 0 ? (
              <Panel title="Inbox">
                <PanelEmpty>
                  {running
                    ? 'The engines are computing a proposal.'
                    : 'Nothing is waiting. Record a disruption to get a reallocation proposal.'}
                </PanelEmpty>
              </Panel>
            ) : (
              pending.map((p) => (
                <ProposalCard
                  key={p.id}
                  projectId={projectId}
                  payload={p.payload}
                  heading={describeDisruption(p.disruption, names)}
                />
              ))
            )}
            {decided.length > 0 ? (
              <Panel title="Decided">
                <ul className="divide-y">
                  {decided.map((p) => (
                    <li
                      key={p.id}
                      className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2.5"
                    >
                      <span className="min-w-0 flex-1">
                        {describeDisruption(p.disruption, names)}
                      </span>
                      <span className={`micro-label ${STATUS_TONE[p.status]}`}>{p.status}</span>
                      <span className="numeric text-xs text-muted-foreground">
                        {p.decided_by ?? ''}{' '}
                        {p.decided_at ? formatDate(p.decided_at.slice(0, 10)) : ''}
                      </span>
                      {p.reason ? (
                        <span className="w-full text-xs text-muted-foreground">“{p.reason}”</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </Panel>
            ) : null}
          </div>
        </div>
      </div>
    </>
  )
}
