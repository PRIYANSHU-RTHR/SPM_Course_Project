import { TableCell, TableRow } from '@/components/ui/table'
import type { PlannedTask, PlanReview } from '@/lib/api/schemas'
import { formatHours, formatShortDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { estimateError, type TaskEdit } from './planModel'
import { SkillsEditor } from './SkillsEditor'

const HOURS =
  'h-7 w-14 rounded-md border border-input bg-surface-2 px-1.5 text-right font-mono text-xs tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-ring'

interface WbsTaskRowProps {
  task: PlannedTask
  edited: boolean
  review: PlanReview
  vocabulary: string[]
  onEdit: (taskId: string, edit: TaskEdit) => void
}

export function WbsTaskRow({ task, edited, review, vocabulary, onEdit }: WbsTaskRowProps) {
  const estimate = review.estimates.tasks.find((t) => t.task_id === task.local_id)
  const placed = review.schedule.tasks.find((t) => t.task_id === task.local_id)
  const owner = review.recommendations.items.find((r) => r.task_id === task.local_id)
  const error = edited ? estimateError(task.o, task.m, task.p) : null

  const hours = (key: 'o' | 'm' | 'p') => (
    <input
      type="number"
      inputMode="decimal"
      step={0.5}
      aria-label={`${task.local_id} ${key} hours`}
      aria-invalid={error ? true : undefined}
      className={cn(HOURS, error && 'border-danger')}
      value={Number.isFinite(task[key]) ? task[key] : ''}
      onChange={(e) => onEdit(task.local_id, { [key]: e.target.valueAsNumber })}
    />
  )

  return (
    <TableRow className={cn(edited && 'bg-surface-2')}>
      <TableCell className="font-mono text-xs text-muted-foreground">
        {task.local_id}
        {placed?.critical ? (
          <span className="ml-1 text-brand" title="On the critical path">
            ●
          </span>
        ) : null}
      </TableCell>
      <TableCell className="min-w-72 py-2 whitespace-normal">
        <span className="block">{task.title}</span>
        {task.predecessors && task.predecessors.length > 0 ? (
          <span className="block font-mono text-[11px] text-subtle">
            after {task.predecessors.join(', ')}
          </span>
        ) : null}
        <div className="mt-1.5">
          <SkillsEditor
            taskId={task.local_id}
            skills={task.required_skills ?? []}
            vocabulary={vocabulary}
            onChange={(skills) => onEdit(task.local_id, { required_skills: skills })}
          />
        </div>
        {error ? <span className="mt-1 block text-xs text-danger">{error}</span> : null}
      </TableCell>
      <TableCell>
        <div className="flex gap-1">
          {hours('o')}
          {hours('m')}
          {hours('p')}
        </div>
      </TableCell>
      <TableCell className="numeric text-right">
        {estimate ? formatHours(estimate.te_hours) : '—'}
      </TableCell>
      <TableCell className="numeric whitespace-nowrap text-muted-foreground">
        {placed ? `${formatShortDate(placed.start)} – ${formatShortDate(placed.end)}` : '—'}
      </TableCell>
      <TableCell className="whitespace-nowrap">
        {owner?.member_name ?? <span className="text-warning">Nobody eligible</span>}
        {owner?.score ? (
          <span className="numeric ml-1 text-xs text-subtle">{owner.score.total.toFixed(0)}</span>
        ) : null}
      </TableCell>
    </TableRow>
  )
}
