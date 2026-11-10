import { OwnerChip } from '@/components/OwnerChip'
import { TaskStatusBadge } from '@/components/TaskStatusBadge'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { formatDate, formatHours, formatTaskId } from '@/lib/format'
import type { Plan, PlanTask } from './plan'

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="micro-label">{label}</dt>
      <dd className="numeric mt-0.5">{value}</dd>
    </div>
  )
}

function TaskLinks({
  title,
  ids,
  plan,
  onSelect,
}: {
  title: string
  ids: number[]
  plan: Plan
  onSelect: (taskId: number) => void
}) {
  return (
    <section>
      <h3 className="micro-label">{title}</h3>
      {ids.length === 0 ? (
        <p className="mt-1 text-muted-foreground">None</p>
      ) : (
        <ul className="mt-1">
          {ids.map((id) => (
            <li key={id}>
              <button
                type="button"
                onClick={() => onSelect(id)}
                className="flex w-full items-center gap-2 rounded-sm py-1 text-left outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="numeric text-xs text-muted-foreground">{formatTaskId(id)}</span>
                <span className="min-w-0 flex-1 truncate">{plan.byId.get(id)?.title}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

interface TaskSheetProps {
  plan: Plan
  task: PlanTask | undefined
  onSelect: (taskId: number) => void
  onClose: () => void
}

export function TaskSheet({ plan, task, onSelect, onClose }: TaskSheetProps) {
  return (
    <Sheet open={task !== undefined} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="overflow-y-auto">
        {task ? (
          <>
            <SheetHeader>
              <p className="numeric text-xs text-muted-foreground">{formatTaskId(task.id)}</p>
              <SheetTitle>{task.title}</SheetTitle>
              <SheetDescription className="sr-only">
                Schedule details and dependencies for this task.
              </SheetDescription>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <TaskStatusBadge status={task.status} />
                {task.critical ? <Badge>Critical</Badge> : null}
                {task.ownerId !== undefined && task.ownerName ? (
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <OwnerChip id={task.ownerId} name={task.ownerName} decorative />
                    {task.ownerName}
                  </span>
                ) : (
                  <span className="text-subtle">Unassigned</span>
                )}
              </div>
            </SheetHeader>
            <div className="flex flex-col gap-5 px-4 pb-6">
              <dl className="grid grid-cols-2 gap-3">
                <Fact label="Early start" value={formatHours(task.es)} />
                <Fact label="Early finish" value={formatHours(task.ef)} />
                <Fact label="Late start" value={formatHours(task.ls)} />
                <Fact label="Late finish" value={formatHours(task.lf)} />
                <Fact label="Total slack" value={formatHours(task.totalSlack)} />
                <Fact label="Free slack" value={formatHours(task.freeSlack)} />
                <Fact label="Starts" value={formatDate(task.start)} />
                <Fact label="Ends" value={formatDate(task.end)} />
                <Fact label="Te" value={formatHours(task.hours)} />
                <Fact label="Resource delay" value={`${task.resourceDelayDays} days`} />
              </dl>
              <TaskLinks
                title="Depends on"
                ids={task.predecessors}
                plan={plan}
                onSelect={onSelect}
              />
              <TaskLinks title="Blocks" ids={task.successors} plan={plan} onSelect={onSelect} />
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
