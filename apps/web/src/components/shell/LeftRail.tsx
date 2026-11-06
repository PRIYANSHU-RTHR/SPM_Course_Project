import type { ComponentProps } from 'react'
import { Link, useMatch } from 'react-router'
import { type NavItem, navItems } from '@/app/nav'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useCurrentProject } from '@/features/projects/useCurrentProject'
import { cn } from '@/lib/utils'

const FOCUS_RING = 'outline-none focus-visible:ring-2 focus-visible:ring-ring'

type RailLinkProps = Omit<ComponentProps<typeof Link>, 'to'> & { item: NavItem }

/**
 * Uses Link rather than NavLink: TooltipTrigger's asChild merges props as plain strings, which
 * turns NavLink's className function into literal class text.
 */
function RailLink({ item, className, ...props }: RailLinkProps) {
  const { icon: Icon, label, to, exact } = item
  const isActive = useMatch({ path: to, end: exact ?? false }) !== null

  return (
    <Link
      {...props}
      to={to}
      aria-label={label}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'relative flex size-10 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-foreground',
        FOCUS_RING,
        isActive && 'bg-surface-2 text-foreground',
        className,
      )}
    >
      {isActive ? (
        <span aria-hidden className="absolute top-2 bottom-2 -left-2 w-0.5 rounded-sm bg-brand" />
      ) : null}
      <Icon className="size-4" strokeWidth={1.5} />
    </Link>
  )
}

export function LeftRail() {
  const { projectId } = useCurrentProject()

  return (
    <nav
      aria-label="Primary"
      className="sticky top-0 flex h-svh w-14 shrink-0 flex-col items-center gap-1 border-r bg-surface py-2"
    >
      <Link
        to="/projects"
        aria-label="OrchestrAI projects"
        className={cn('mb-2 flex size-10 items-center justify-center rounded-lg', FOCUS_RING)}
      >
        <span className="numeric flex size-7 items-center justify-center rounded-sm bg-brand text-xs font-semibold text-brand-foreground">
          OA
        </span>
      </Link>
      {navItems(projectId).map((item) => (
        <Tooltip key={item.label}>
          <TooltipTrigger asChild>
            <RailLink item={item} />
          </TooltipTrigger>
          <TooltipContent side="right">{item.label}</TooltipContent>
        </Tooltip>
      ))}
    </nav>
  )
}
