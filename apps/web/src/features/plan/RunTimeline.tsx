import { cn } from '@/lib/utils'
import type { StepState, TimelineStep } from './planModel'

const DOT: Record<StepState, string> = {
  running: 'border-brand bg-transparent',
  done: 'border-brand bg-brand',
  waiting: 'border-warning bg-warning',
  failed: 'border-danger bg-danger',
}

const STATE_LABEL: Record<StepState, string> = {
  running: 'running',
  done: 'done',
  waiting: 'waiting for you',
  failed: 'failed',
}

function formatDuration(ms: number | null): string {
  if (ms === null) return ''
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`
}

interface RunTimelineProps {
  steps: TimelineStep[]
  /** Shown while the stream has not produced any node yet. */
  pending: boolean
}

/** Vertical run log: one row per node run, with duration and the node's one-line summary. */
export function RunTimeline({ steps, pending }: RunTimelineProps) {
  if (steps.length === 0) {
    return (
      <p className="px-4 py-3 text-muted-foreground">
        {pending ? 'Starting the planning workflow.' : 'No steps recorded for this run.'}
      </p>
    )
  }
  return (
    <ol className="flex flex-col px-4 py-3" aria-label="Workflow steps">
      {steps.map((step, index) => (
        <li key={step.key} className="relative flex gap-3 pb-4 last:pb-0">
          {index < steps.length - 1 ? (
            <span aria-hidden className="absolute top-4 bottom-0 left-[4.5px] w-px bg-border" />
          ) : null}
          <span
            aria-hidden
            className={cn('mt-1 size-2.5 shrink-0 rounded-full border-2', DOT[step.state])}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className={cn(step.state === 'running' && 'text-foreground')}>
                {step.label}
              </span>
              <span className="numeric shrink-0 font-mono text-xs text-subtle">
                {step.state === 'done' ? formatDuration(step.durationMs) : STATE_LABEL[step.state]}
              </span>
            </div>
            {step.summary ? (
              <p className="mt-0.5 text-xs leading-4 text-muted-foreground">{step.summary}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  )
}
