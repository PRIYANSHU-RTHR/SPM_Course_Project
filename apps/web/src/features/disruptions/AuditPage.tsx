import { Link } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useCurrentProject } from '@/features/projects/useCurrentProject'
import { formatDate, formatProjectId } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useAudit } from './queries'
import { groupByDay, isSystemActor } from './reallocModel'

/** "2026-11-10T09:24:05Z" -> "09:24" (UTC, as stored). */
const time = (iso: string) => iso.slice(11, 16)

export function AuditPage() {
  const { project, projectId, isLoading } = useCurrentProject()
  const audit = useAudit(projectId)

  if (isLoading) return <Skeleton className="h-8 w-72" />
  if (!project || projectId === undefined) {
    return (
      <>
        <PageHeader label="Audit" title="No project yet" />
        <PanelEmpty
          action={
            <Link to="/plan/new" className="text-brand">
              Plan a project
            </Link>
          }
        >
          The audit log belongs to a project.
        </PanelEmpty>
      </>
    )
  }

  const entries = audit.data?.pages.flatMap((page) => page.items) ?? []
  const total = audit.data?.pages[0]?.total ?? 0

  return (
    <>
      <PageHeader label={`Audit · ${formatProjectId(projectId)}`} title={project.name}>
        Every approval, override, reassignment, disruption and clock move: who, what and why.
      </PageHeader>
      <Panel title={total ? `${total} entries` : 'Entries'}>
        {audit.isLoading ? (
          <div className="flex flex-col gap-2 p-4">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : audit.isError ? (
          <PanelError message={audit.error.message} onRetry={() => void audit.refetch()} />
        ) : entries.length === 0 ? (
          <PanelEmpty>Nothing has been recorded for this project yet.</PanelEmpty>
        ) : (
          <div className="flex flex-col">
            {groupByDay(entries).map(({ day, entries: list }) => (
              <section key={day} aria-label={formatDate(day)}>
                <h3 className="micro-label sticky top-0 border-b bg-surface px-4 py-2">
                  {formatDate(day)}
                </h3>
                <ol className="divide-y">
                  {list.map((entry) => {
                    const system = isSystemActor(entry.actor)
                    return (
                      <li key={entry.id} className="flex gap-4 px-4 py-2.5">
                        <span className="numeric w-11 shrink-0 font-mono text-xs leading-5 text-subtle">
                          {time(entry.created_at)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className={cn(system && 'text-muted-foreground')}>{entry.summary}</p>
                          {entry.reason ? (
                            <p className="text-xs text-muted-foreground">“{entry.reason}”</p>
                          ) : null}
                        </div>
                        <span className="hidden shrink-0 font-mono text-[11px] leading-5 text-subtle sm:block">
                          {entry.action}
                        </span>
                      </li>
                    )
                  })}
                </ol>
              </section>
            ))}
            {audit.hasNextPage ? (
              <div className="border-t px-4 py-3">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={audit.isFetchingNextPage}
                  onClick={() => void audit.fetchNextPage()}
                >
                  {audit.isFetchingNextPage
                    ? 'Loading'
                    : `Load older (${total - entries.length} more)`}
                </Button>
              </div>
            ) : null}
          </div>
        )}
      </Panel>
    </>
  )
}
