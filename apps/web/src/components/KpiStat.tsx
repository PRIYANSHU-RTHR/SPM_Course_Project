import { TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface KpiStatProps {
  label: string
  value: ReactNode
  /** Change since the last snapshot, already formatted, e.g. "+0.01". */
  delta?: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
  /** Set only when the value is out of range. Colours it and adds a warning icon. */
  status?: 'warning' | 'danger'
  /** Formula or definition, shown in a tooltip. */
  hint?: string
}

const TONE = {
  neutral: 'text-muted-foreground',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
} as const

const CARD = 'rounded-xl border bg-surface p-4 text-left'

export function KpiStat({ label, value, delta, tone = 'neutral', status, hint }: KpiStatProps) {
  const stat = (
    <div className={CARD}>
      <p className="micro-label flex items-center gap-1.5">
        {label}
        {status ? (
          <TriangleAlert
            aria-label="Out of range"
            className={cn('size-3', TONE[status])}
            strokeWidth={1.5}
          />
        ) : null}
      </p>
      <p className={cn('numeric mt-2 text-2xl leading-8', status && TONE[status])}>{value}</p>
      <p className={cn('numeric mt-1 min-h-4 text-xs leading-4', TONE[tone])}>{delta}</p>
    </div>
  )

  if (!hint) return stat

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="block w-full rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {stat}
        </button>
      </TooltipTrigger>
      <TooltipContent className="numeric max-w-64">{hint}</TooltipContent>
    </Tooltip>
  )
}

/** Same size as a KpiStat, so the strip does not move when data arrives. */
export function KpiStatSkeleton() {
  return (
    <div className={CARD}>
      <Skeleton className="my-0.5 h-3 w-16" />
      <Skeleton className="mt-2.5 h-7 w-20" />
      <Skeleton className="mt-1.5 h-3 w-10" />
    </div>
  )
}
