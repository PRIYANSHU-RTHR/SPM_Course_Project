import { OwnerChip } from '@/components/OwnerChip'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { TaskStatusBadge } from '@/components/TaskStatusBadge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatHours, formatTaskId } from '@/lib/format'
import { nextCritical } from './metrics'
import { useCpm, useMembers, useProjectFull } from './queries'

export function CriticalTasksPanel({ projectId }: { projectId: number }) {
  const cpm = useCpm(projectId)
  const full = useProjectFull(projectId)
  const members = useMembers()
  const isLoading = cpm.isLoading || full.isLoading
  const failed = cpm.error ?? full.error
  const rows = cpm.data && full.data ? nextCritical(cpm.data, full.data) : []
  const names = new Map(members.data?.items.map((member) => [member.id, member.name]))

  return (
    <Panel
      title="Next on the critical path"
      action={{ label: 'Schedule', to: `/projects/${projectId}/schedule` }}
      className="lg:col-span-3"
    >
      {isLoading ? (
        <div className="flex flex-col gap-2 p-3">
          {[0, 1, 2, 3, 4].map((row) => (
            <Skeleton key={row} className="h-7 w-full" />
          ))}
        </div>
      ) : failed ? (
        <PanelError
          message={failed.message}
          onRetry={() => {
            void cpm.refetch()
            void full.refetch()
          }}
        />
      ) : rows.length === 0 ? (
        <PanelEmpty>Every task on the critical path is done.</PanelEmpty>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20">ID</TableHead>
              <TableHead>Task</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Owner</TableHead>
              <TableHead className="text-right">Te</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(({ task, hours, ownerId }) => {
              const name = ownerId === undefined ? undefined : names.get(ownerId)
              return (
                <TableRow key={task.id}>
                  <TableCell className="numeric text-muted-foreground">
                    {formatTaskId(task.id)}
                  </TableCell>
                  <TableCell>{task.title}</TableCell>
                  <TableCell>
                    <TaskStatusBadge status={task.status} />
                  </TableCell>
                  <TableCell>
                    {ownerId !== undefined && name ? (
                      <OwnerChip id={ownerId} name={name} />
                    ) : (
                      <span className="text-subtle">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell className="numeric text-right">{formatHours(hours)}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}
    </Panel>
  )
}
