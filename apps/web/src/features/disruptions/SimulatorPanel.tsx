import { useState } from 'react'
import { Panel } from '@/components/Panel'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMembers, useProjectFull } from '@/features/projects/queries'
import { formatDate, formatPercent, formatRatio } from '@/lib/format'
import { ScopeForm, SlipForm } from './DisruptionForms'
import { Field } from './fields'
import { LeaveForm } from './LeaveForm'
import { useAdvanceClock } from './queries'

function ClockForm({ projectId, today }: { projectId: number; today: string }) {
  const advance = useAdvanceClock(projectId)
  const [days, setDays] = useState('14')
  const n = Number(days)
  const result = advance.data

  return (
    <div className="flex flex-col gap-3">
      <p className="text-muted-foreground">
        Project clock: <span className="numeric text-foreground">{formatDate(today)}</span>. Each
        working day books the planned hours with seeded efficiency and cost factors, then EVM, risks
        and the forecast are recomputed.
      </p>
      <div className="flex flex-wrap items-end gap-2">
        {[7, 14].map((preset) => (
          <Button
            key={preset}
            variant="outline"
            disabled={advance.isPending}
            onClick={() => advance.mutate(preset)}
          >
            +{preset} days
          </Button>
        ))}
        <Field id="clock-days" label="Days">
          <Input
            id="clock-days"
            type="number"
            min={1}
            max={90}
            className="numeric w-20 text-right"
            value={days}
            onChange={(e) => setDays(e.target.value)}
          />
        </Field>
        <Button
          disabled={advance.isPending || !(n >= 1 && n <= 90)}
          onClick={() => advance.mutate(n)}
        >
          {advance.isPending ? 'Advancing' : 'Advance'}
        </Button>
      </div>
      {result ? (
        <p className="numeric text-muted-foreground">
          {formatDate(result.from_date)} → {formatDate(result.to_date)}: {result.working_days}{' '}
          working days, SPI {formatRatio(result.spi)}, CPI {formatRatio(result.cpi)}, P(on time){' '}
          {formatPercent(result.p_on_time)}.
        </p>
      ) : null}
      {advance.isError ? <p className="text-danger">{advance.error.message}</p> : null}
    </div>
  )
}

interface SimulatorPanelProps {
  projectId: number
  today: string
  blocked: boolean
  onStarted: (threadId: string) => void
}

/** Leave, slip, new scope (each starts a reallocation run) and the simulated clock. */
export function SimulatorPanel({ projectId, today, blocked, onStarted }: SimulatorPanelProps) {
  const full = useProjectFull(projectId)
  const members = useMembers()

  return (
    <Panel title="Disruption simulator">
      <div className="p-4">
        {full.data && members.data ? (
          <Tabs defaultValue="leave">
            <TabsList>
              <TabsTrigger value="leave">Leave</TabsTrigger>
              <TabsTrigger value="slip">Slip</TabsTrigger>
              <TabsTrigger value="scope">New scope</TabsTrigger>
              <TabsTrigger value="clock">Clock</TabsTrigger>
            </TabsList>
            {(['leave', 'slip', 'scope'] as const).map((tab) => {
              const Form = { leave: LeaveForm, slip: SlipForm, scope: ScopeForm }[tab]
              return (
                <TabsContent key={tab} value={tab} className="pt-3">
                  {blocked ? (
                    <p className="mb-3 text-warning">
                      A proposal is waiting for your decision. Approve or reject it first.
                    </p>
                  ) : null}
                  <Form
                    projectId={projectId}
                    today={today}
                    full={full.data}
                    members={members.data.items}
                    blocked={blocked}
                    onStarted={onStarted}
                  />
                </TabsContent>
              )
            })}
            <TabsContent value="clock" className="pt-3">
              <ClockForm projectId={projectId} today={today} />
            </TabsContent>
          </Tabs>
        ) : full.isError || members.isError ? (
          <p className="text-danger">{(full.error ?? members.error)?.message}</p>
        ) : (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}
      </div>
    </Panel>
  )
}
