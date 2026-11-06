import type { ReactNode } from 'react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface KpiStatProps {
  label: string
  value: ReactNode
  /** Change since the last snapshot, already formatted, e.g. "+4 pts". */
  delta?: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
  /** Formula or definition, shown in a tooltip. */
  hint?: string
}

const TONE = {
  neutral: 'text-muted-foreground',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
} as const

export function KpiStat({ label, value, delta, tone = 'neutral', hint }: KpiStatProps) {
  const stat = (
    <div className="rounded-xl border bg-surface p-4 text-left">
      <p className="micro-label">{label}</p>
      <p className="numeric mt-2 text-2xl leading-8">{value}</p>
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
      <TooltipContent className="numeric">{hint}</TooltipContent>
    </Tooltip>
  )
}
