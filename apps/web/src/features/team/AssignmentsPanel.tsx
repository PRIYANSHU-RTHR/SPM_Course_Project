import { useState } from 'react'
import { OwnerChip } from '@/components/OwnerChip'
import { PanelError } from '@/components/Panel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { type AssignmentMode, useRecommendations } from '@/features/projects/queries'
import type { Member, ProjectFull } from '@/lib/api/schemas'
import { formatRatio, formatTaskId } from '@/lib/format'
import { ModeCompare } from './ModeCompare'
import { RecommendationSheet } from './RecommendationSheet'
import { assignmentRows, storedScore } from './teamMetrics'

interface AssignmentsPanelProps {
  full: ProjectFull
  members: Member[]
}

export function AssignmentsPanel({ full, members }: AssignmentsPanelProps) {
  const projectId = full.project.id
  const [mode, setMode] = useState<AssignmentMode>('optimal')
  const [selected, setSelected] = useState<number | null>(null)
  const recommend = useRecommendations(projectId, mode)
  const rows = assignmentRows(full, recommend.data)
  const names = new Map(members.map((member) => [member.id, member.name]))
  const row = rows.find((item) => item.task.id === selected)

  const chip = (id: number | null | undefined) => {
    const name = id == null ? undefined : names.get(id)
    return id != null && name ? (
      <OwnerChip id={id} name={name} />
    ) : (
      <span className="text-subtle">Unassigned</span>
    )
  }

  return (
    <section className="flex min-w-0 flex-col rounded-xl border bg-surface">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2">
        <h2 className="text-[15px] leading-5 font-semibold">Assignments</h2>
        <div role="group" aria-label="Assignment mode" className="flex gap-1">
          {(['greedy', 'optimal'] as const).map((level) => (
            <Button
              key={level}
              variant={mode === level ? 'secondary' : 'ghost'}
              size="sm"
              aria-pressed={mode === level}
              onClick={() => setMode(level)}
            >
              {level === 'greedy' ? 'Greedy' : 'Optimal'}
            </Button>
          ))}
        </div>
      </header>
      {recommend.isError ? (
        <PanelError message={recommend.error.message} onRetry={() => void recommend.refetch()} />
      ) : recommend.data ? (
        <ModeCompare comparison={recommend.data.comparison} mode={mode} />
      ) : (
        <Skeleton className="m-3 h-14" />
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-20">ID</TableHead>
            <TableHead>Task</TableHead>
            <TableHead>Owner</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Recommended</TableHead>
            <TableHead className="text-right">Rec. score</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(({ task, assignment, recommendation }) => {
            const score = assignment ? storedScore(assignment.score_breakdown) : null
            return (
              <TableRow
                key={task.id}
                className="cursor-pointer"
                onClick={() => setSelected(task.id)}
              >
                <TableCell className="numeric text-muted-foreground">
                  {formatTaskId(task.id)}
                </TableCell>
                <TableCell className="max-w-80">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      setSelected(task.id)
                    }}
                    className="block max-w-full cursor-pointer truncate rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {task.title}
                  </button>
                </TableCell>
                <TableCell>{chip(assignment?.member_id)}</TableCell>
                <TableCell className="numeric text-right">{formatRatio(score, 1)}</TableCell>
                <TableCell>
                  {assignment ? (
                    <Badge variant={assignment.source === 'ai' ? 'outline' : 'default'}>
                      {assignment.source === 'ai' ? 'AI' : 'PM override'}
                    </Badge>
                  ) : (
                    <span className="text-subtle">—</span>
                  )}
                </TableCell>
                <TableCell>{chip(recommendation?.member_id)}</TableCell>
                <TableCell className="numeric text-right text-muted-foreground">
                  {formatRatio(recommendation?.score?.total, 1)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {row ? (
        <RecommendationSheet
          key={`${row.task.id}-${mode}`}
          projectId={projectId}
          mode={mode}
          row={row}
          members={members}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </section>
  )
}
