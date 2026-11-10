import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { ProposalItem } from '@/lib/api/schemas'
import { formatShortDate, formatTaskId } from '@/lib/format'
import { cn } from '@/lib/utils'
import { REASON_LABEL } from './reallocModel'

const arrow = <span className="mx-1 text-subtle">→</span>

function score(value: number | null) {
  return value === null ? '—' : value.toFixed(0)
}

/** Per affected task: owner, assignment score and planned finish, before -> if approved. */
export function ProposalDiff({ items }: { items: ProposalItem[] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="bg-surface-2">
          <TableRow>
            <TableHead>Task</TableHead>
            <TableHead>Why</TableHead>
            <TableHead>Owner</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead className="text-right">Finish</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            const later = (item.finish_after ?? '') > (item.finish_before ?? '')
            return (
              <TableRow key={item.task_id}>
                <TableCell className="min-w-56 whitespace-normal">
                  <span className="mr-2 font-mono text-xs text-muted-foreground">
                    {formatTaskId(item.task_id)}
                  </span>
                  {item.title}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {item.reasons.map((r) => REASON_LABEL[r]).join(', ')}
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  {item.changed ? (
                    <>
                      <span
                        className={cn(
                          item.before.member_id !== null &&
                            !item.before_eligible &&
                            'text-subtle line-through',
                        )}
                        title={item.before_ineligible_reason ?? undefined}
                      >
                        {item.before.name ?? 'Unassigned'}
                      </span>
                      {arrow}
                      <span className="text-foreground">{item.after.name}</span>
                    </>
                  ) : (
                    <span className="text-muted-foreground">
                      Keep {item.before.name ?? 'unassigned'}
                    </span>
                  )}
                </TableCell>
                <TableCell className="numeric text-right whitespace-nowrap">
                  {score(item.score_before)}
                  {item.changed ? (
                    <>
                      {arrow}
                      {score(item.score_after)}
                    </>
                  ) : null}
                </TableCell>
                <TableCell className="numeric text-right whitespace-nowrap">
                  {formatShortDate(item.finish_before)}
                  {arrow}
                  <span className={cn(later ? 'text-warning' : 'text-foreground')}>
                    {formatShortDate(item.finish_after)}
                  </span>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
