import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface PanelProps {
  title: string
  action?: { label: string; to: string }
  className?: string
  children: ReactNode
}

export function Panel({ title, action, className, children }: PanelProps) {
  return (
    <section className={cn('flex min-w-0 flex-col rounded-xl border bg-surface', className)}>
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-[15px] leading-5 font-semibold">{title}</h2>
        {action ? (
          <Link
            to={action.to}
            className="shrink-0 rounded-sm text-brand underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
          >
            {action.label}
          </Link>
        ) : null}
      </header>
      {children}
    </section>
  )
}

interface PanelMessageProps {
  children: ReactNode
  action?: ReactNode
}

/** One sentence and one action, for empty sections. */
export function PanelEmpty({ children, action }: PanelMessageProps) {
  return (
    <div className="flex flex-col items-start gap-3 p-4">
      <p className="text-muted-foreground">{children}</p>
      {action}
    </div>
  )
}

export function PanelError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3 p-4">
      <p className="text-danger">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  )
}
