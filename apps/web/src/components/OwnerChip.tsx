import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { initials } from '@/lib/format'
import { ownerColour } from '@/lib/tokens'

interface OwnerChipProps {
  id: number
  name: string
  /** For places that already show the name: no tooltip and no keyboard stop. */
  decorative?: boolean
}

const CHIP =
  'numeric inline-flex size-6 items-center justify-center rounded-sm text-[11px] font-medium text-background outline-none focus-visible:ring-2 focus-visible:ring-ring'

export function OwnerChip({ id, name, decorative = false }: OwnerChipProps) {
  if (decorative) {
    return (
      <span aria-hidden className={CHIP} style={{ background: ownerColour(id) }}>
        {initials(name)}
      </span>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          aria-label={name}
          className={CHIP}
          style={{ background: ownerColour(id) }}
        >
          {initials(name)}
        </span>
      </TooltipTrigger>
      <TooltipContent>{name}</TooltipContent>
    </Tooltip>
  )
}
