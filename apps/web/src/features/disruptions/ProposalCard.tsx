import { useState } from 'react'
import { Panel } from '@/components/Panel'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { ProposalPayload, RiskRef, ScenarioMetrics } from '@/lib/api/schemas'
import { formatPercent, formatShortDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { ProposalDiff } from './ProposalDiff'
import { useDecideProposal } from './queries'
import { formatPoints, pointsDelta } from './reallocModel'

const COLUMNS = [
  ['before_disruption', 'Before disruption'],
  ['now', 'Now'],
  ['if_approved', 'If approved'],
] as const

function MetricColumns({ payload }: { payload: ProposalPayload }) {
  const delta = pointsDelta(payload.now.p_on_time, payload.if_approved.p_on_time)
  return (
    <dl className="grid grid-cols-3 divide-x rounded-lg border">
      {COLUMNS.map(([key, label]) => {
        const m: ScenarioMetrics = payload[key]
        const approved = key === 'if_approved'
        return (
          <div key={key} className={cn('flex flex-col gap-1 p-3', approved && 'bg-surface-2')}>
            <dt className="micro-label">{label}</dt>
            <dd className="numeric font-mono text-xl leading-7">
              {formatPercent(m.p_on_time)}
              {approved && delta ? (
                <span className={cn('ml-2 text-xs', delta > 0 ? 'text-success' : 'text-danger')}>
                  {formatPoints(delta)}
                </span>
              ) : null}
            </dd>
            <dd className="numeric text-xs text-muted-foreground">
              finish {formatShortDate(m.finish)} · P80 {formatShortDate(m.p80)}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}

function RiskList({ title, risks, tone }: { title: string; risks: RiskRef[]; tone: string }) {
  if (risks.length === 0) return null
  return (
    <div>
      <p className="micro-label mb-1">{title}</p>
      <ul className="flex flex-col gap-0.5">
        {risks.map((r) => (
          <li key={`${r.rule_key}-${r.subject_ref}`} className={tone}>
            <span className="numeric mr-2 font-mono text-xs">{r.score}</span>
            {r.title}
          </li>
        ))}
      </ul>
    </div>
  )
}

interface ProposalCardProps {
  projectId: number
  payload: ProposalPayload
  /** What happened, in words (e.g. "Aarav Mehta on leave 09 Nov – 20 Nov"). */
  heading: string
}

export function ProposalCard({ projectId, payload, heading }: ProposalCardProps) {
  const decide = useDecideProposal(projectId)
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const moves = payload.items.filter((i) => i.changed).length
  const send = (decision: Parameters<typeof decide.mutate>[0]['decision']) =>
    decide.mutate({ threadId: payload.thread_id, decision })

  return (
    <Panel title={heading}>
      <div className="flex flex-col gap-4 p-4">
        <p className="text-muted-foreground">
          <span className="micro-label mr-2">engine · summary</span>
          {payload.summary}
        </p>
        <MetricColumns payload={payload} />
        {payload.if_approved.finish > payload.now.finish ? (
          <p className="rounded-lg border border-warning/40 px-3 py-2 text-warning">
            Approving finishes later ({formatShortDate(payload.if_approved.finish)}) than keeping
            the current owners ({formatShortDate(payload.now.finish)}). The engine optimises skill
            fit, capacity and balance, not the finish date; consider rejecting.
          </p>
        ) : null}
        <ProposalDiff items={payload.items} />
        <div className="grid gap-3 md:grid-cols-2">
          <RiskList
            title="Risks that would close"
            risks={payload.risks_that_would_close}
            tone="text-success"
          />
          <RiskList
            title="Risks that would open"
            risks={payload.risks_that_would_open}
            tone="text-warning"
          />
        </div>
        {rejecting ? (
          <div className="flex flex-col gap-2">
            <label htmlFor="proposal-reason" className="micro-label">
              Why reject (owners stay as they are)
            </label>
            <Textarea
              id="proposal-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="flex gap-2">
              <Button
                variant="destructive"
                disabled={!reason.trim() || decide.isPending}
                onClick={() => send({ action: 'reject', reason: reason.trim() })}
              >
                Reject proposal
              </Button>
              <Button variant="ghost" onClick={() => setRejecting(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button disabled={decide.isPending} onClick={() => send({ action: 'approve' })}>
              {decide.isPending
                ? 'Applying'
                : `Approve ${moves} reassignment${moves === 1 ? '' : 's'}`}
            </Button>
            <Button variant="ghost" onClick={() => setRejecting(true)}>
              Reject
            </Button>
          </div>
        )}
        {decide.isError ? <p className="text-danger">{decide.error.message}</p> : null}
      </div>
    </Panel>
  )
}
