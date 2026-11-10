import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { Button, buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useProjectFull, useRefreshRisks, useRisks } from '@/features/projects/queries'
import { ApiError } from '@/lib/api/client'
import { RiskMatrix } from './RiskMatrix'
import { type Cell, cellCounts, filterByCell, sortRegister } from './riskMetrics'
import { RiskRegister } from './RiskRegister'
import { RiskSheet } from './RiskSheet'

const LINK_BUTTON = buttonVariants({ variant: 'outline', size: 'sm' })

function RisksContent({ projectId }: { projectId: number }) {
  const risks = useRisks(projectId)
  const refresh = useRefreshRisks(projectId)
  const [cell, setCell] = useState<Cell | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const items = useMemo(() => risks.data?.items ?? [], [risks.data])
  const rows = useMemo(() => filterByCell(sortRegister(items), cell), [items, cell])
  const detect = (
    <Button
      variant="outline"
      size="sm"
      disabled={refresh.isPending}
      onClick={() => refresh.mutate()}
    >
      {refresh.isPending ? 'Running detection' : 'Run detection'}
    </Button>
  )

  if (risks.isLoading) return <Skeleton className="h-96 w-full" />
  if (risks.isError) {
    return (
      <Panel title="Risk register">
        <PanelError message={risks.error.message} onRetry={() => void risks.refetch()} />
      </Panel>
    )
  }
  if (items.length === 0) {
    return (
      <Panel title="Risk register">
        <PanelEmpty action={detect}>
          {refresh.isError ? refresh.error.message : 'No risks are recorded.'}
        </PanelEmpty>
      </Panel>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-[320px_minmax(0,1fr)]">
      <Panel title="P × I matrix" className="self-start">
        <RiskMatrix counts={cellCounts(items)} selected={cell} onSelect={setCell} />
      </Panel>
      <section className="flex min-w-0 flex-col rounded-xl border bg-surface">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2">
          <div className="flex items-center gap-3">
            <h2 className="text-[15px] leading-5 font-semibold">Risk register</h2>
            {cell ? (
              <Button variant="ghost" size="sm" onClick={() => setCell(null)}>
                Clear filter: P{cell.probability} × I{cell.impact}
              </Button>
            ) : null}
          </div>
          {detect}
        </header>
        <RiskRegister risks={rows} onSelect={setSelected} />
      </section>
      <RiskSheet
        key={selected ?? 'none'}
        projectId={projectId}
        risk={items.find((risk) => risk.id === selected)}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}

export function RisksPage() {
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

  return (
    <>
      <PageHeader label="Risks" title={full.data?.project.name ?? 'Risk register'} />
      <RisksContent projectId={projectId} />
    </>
  )
}

