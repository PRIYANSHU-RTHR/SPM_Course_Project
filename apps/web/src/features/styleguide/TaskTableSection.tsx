import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useProjectFull } from '@/features/projects/queries'
import { useCurrentProject } from '@/features/projects/useCurrentProject'
import type { Task, TaskStatus } from '@/lib/api/provisional'
import { formatHours, formatTaskId } from '@/lib/format'
import { Section } from './Section'

type StatusStyle = { label: string; variant: 'outline' | 'secondary' | 'success' | 'warning' }

const STATUS: Record<TaskStatus, StatusStyle> = {
  todo: { label: 'Todo', variant: 'outline' },
  in_progress: { label: 'In progress', variant: 'secondary' },
  blocked: { label: 'Blocked', variant: 'warning' },
  done: { label: 'Done', variant: 'success' },
}

/** PERT expected hours, for display here only. The estimation engine owns this in the app. */
function expectedHours(task: Task) {
  return (task.optimistic_hours + 4 * task.most_likely_hours + task.pessimistic_hours) / 6
}

export function TaskTableSection() {
  const current = useCurrentProject()
  const full = useProjectFull(current.projectId)
  const isLoading = current.isLoading || full.isLoading
  const isError = current.isError || full.isError
  const data = full.data

  return (
    <Section title="Table">
      <div className="overflow-hidden rounded-xl border bg-surface [&_[data-slot=table-container]]:max-h-96">
        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2, 3].map((row) => (
              <Skeleton key={row} className="h-7 w-full" />
            ))}
          </div>
        ) : isError ? (
          <p className="p-4 text-danger">{full.error?.message ?? 'Could not load projects'}</p>
        ) : !data || data.tasks.length === 0 ? (
          <p className="p-4 text-muted-foreground">This project has no tasks yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">ID</TableHead>
                <TableHead>Task</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Te</TableHead>
                <TableHead className="text-right">Done</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="numeric text-muted-foreground">
                    {formatTaskId(task.id)}
                  </TableCell>
                  <TableCell>{task.title}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS[task.status].variant}>{STATUS[task.status].label}</Badge>
                  </TableCell>
                  <TableCell className="numeric text-right">
                    {formatHours(expectedHours(task))}
                  </TableCell>
                  <TableCell className="numeric text-right">{task.percent_complete}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </Section>
  )
}
