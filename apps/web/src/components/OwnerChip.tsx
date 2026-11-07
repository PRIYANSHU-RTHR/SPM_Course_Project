import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { initials } from '@/lib/format'
import { ownerColour } from '@/lib/tokens'

export function OwnerChip({ id, name }: { id: number; name: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          tabIndex={0}
          aria-label={name}
          className="numeric inline-flex size-6 items-center justify-center rounded-sm text-[11px] font-medium text-background outline-none focus-visible:ring-2 focus-visible:ring-ring"
          style={{ background: ownerColour(id) }}
        >
          {initials(name)}
        </span>
      </TooltipTrigger>
      <TooltipContent>{name}</TooltipContent>
    </Tooltip>
  )
}
