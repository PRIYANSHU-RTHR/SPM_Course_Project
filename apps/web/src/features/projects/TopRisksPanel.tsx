import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { openRisks } from './metrics'
import { useRefreshRisks, useRisks } from './queries'

export function TopRisksPanel({ projectId }: { projectId: number }) {
  const risks = useRisks(projectId)
  const refresh = useRefreshRisks(projectId)
  const rows = risks.data ? openRisks(risks.data.items).slice(0, 3) : []

  return (
    <Panel
      title="Top risks"
      action={{ label: 'Register', to: `/projects/${projectId}/risks` }}
      className="lg:col-span-3"
    >
      {risks.isLoading ? (
        <div className="flex flex-col gap-2 p-3">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} className="h-10 w-full" />
          ))}
        </div>
      ) : risks.isError ? (
        <PanelError message={risks.error.message} onRetry={() => void risks.refetch()} />
      ) : rows.length === 0 ? (
        <PanelEmpty
          action={
            <Button
              variant="outline"
              size="sm"
              disabled={refresh.isPending}
              onClick={() => refresh.mutate()}
            >
              {refresh.isPending ? 'Running detection' : 'Run detection'}
            </Button>
          }
        >
          {refresh.isError ? refresh.error.message : 'No open risks are recorded.'}
        </PanelEmpty>
      ) : (
        <ol className="divide-y">
          {rows.map((risk) => (
            <li key={risk.id} className="flex items-start gap-3 px-4 py-3">
              <span
                className="numeric w-7 shrink-0 text-right text-[15px] leading-5"
                aria-label={`Score ${risk.score} of 25`}
              >
                {risk.score}
              </span>
              <div className="min-w-0">
                <p>{risk.title}</p>
                <p className="micro-label mt-0.5">
                  {risk.category} · P{risk.probability} × I{risk.impact}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  )
}
