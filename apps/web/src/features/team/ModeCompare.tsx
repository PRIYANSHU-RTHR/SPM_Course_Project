import type { RecommendResponse } from '@/lib/api/schemas'
import type { AssignmentMode } from '@/features/projects/queries'
import { formatDelta } from '@/lib/format'
import { cn } from '@/lib/utils'
import { compareModes } from './teamMetrics'

interface ModeCompareProps {
  comparison: RecommendResponse['comparison']
  mode: AssignmentMode
}

export function ModeCompare({ comparison, mode }: ModeCompareProps) {
  return (
    <dl className="grid grid-cols-1 border-b sm:grid-cols-3">
      {compareModes(comparison).map(({ label, greedy, optimal, delta, digits }) => (
        <div key={label} className="border-b px-4 py-3 last:border-0 sm:border-r sm:border-b-0 sm:last:border-r-0">
          <dt className="micro-label">{label}</dt>
          <dd className="numeric mt-1 flex items-baseline justify-between gap-3">
            <span>
              <span className={cn(mode !== 'greedy' && 'text-muted-foreground')}>
                Greedy {greedy}
              </span>
              <span className="mx-2 text-subtle">·</span>
              <span className={cn(mode !== 'optimal' && 'text-muted-foreground')}>
                Optimal {optimal}
              </span>
            </span>
            <span className="text-xs text-muted-foreground" title="Optimal minus greedy">
              {formatDelta(delta, digits)}
            </span>
          </dd>
        </div>
      ))}
    </dl>
  )
}
