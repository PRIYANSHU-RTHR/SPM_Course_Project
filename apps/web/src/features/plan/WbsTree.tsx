import { Fragment } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { PlanReview } from '@/lib/api/schemas'
import { editedTask, type Edits, type TaskEdit } from './planModel'
import { WbsTaskRow } from './WbsTaskRow'

interface WbsTreeProps {
  review: PlanReview
  edits: Edits
  vocabulary: string[]
  onEdit: (taskId: string, edit: TaskEdit) => void
}

/** The draft WBS by epic. o/m/p and skills are editable; te, dates and owners are engine output. */
export function WbsTree({ review, edits, vocabulary, onEdit }: WbsTreeProps) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-surface-2">
          <TableRow>
            <TableHead className="w-20">ID</TableHead>
            <TableHead>Task and required skills</TableHead>
            <TableHead>
              <span title="Optimistic, most likely, pessimistic hours">o / m / p</span>
            </TableHead>
            <TableHead className="text-right">
              <span title="PERT te = (o + 4m + p) / 6">te</span>
            </TableHead>
            <TableHead>Window</TableHead>
            <TableHead>Owner</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {review.wbs.epics.map((epic) => (
            <Fragment key={epic.local_id}>
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={6} className="bg-surface pt-4 pb-1.5">
                  <span className="micro-label mr-2">{epic.local_id}</span>
                  <span className="font-semibold">{epic.title}</span>
                </TableCell>
              </TableRow>
              {epic.tasks.map((task) => (
                <WbsTaskRow
                  key={task.local_id}
                  task={editedTask(task, edits[task.local_id])}
                  edited={edits[task.local_id] !== undefined}
                  review={review}
                  vocabulary={vocabulary}
                  onEdit={onEdit}
                />
              ))}
            </Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
