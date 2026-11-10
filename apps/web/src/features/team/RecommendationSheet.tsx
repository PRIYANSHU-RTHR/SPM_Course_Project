import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { type AssignmentMode, useApplyAssignment } from '@/features/projects/queries'
import type { Member } from '@/lib/api/schemas'
import { formatDate, formatTaskId } from '@/lib/format'
import { CandidateCard } from './CandidateCard'
import { ExplanationBlock } from './ExplanationBlock'
import { type AssignmentRow, toBreakdown } from './teamMetrics'

interface RecommendationSheetProps {
  projectId: number
  mode: AssignmentMode
  row: AssignmentRow
  members: Member[]
  onClose: () => void
}

export function RecommendationSheet({
  projectId,
  mode,
  row,
  members,
  onClose,
}: RecommendationSheetProps) {
  const { task, assignment, recommendation } = row
  const apply = useApplyAssignment(projectId)
  const [overriding, setOverriding] = useState(false)
  const [memberId, setMemberId] = useState('')
  const [reason, setReason] = useState('')
  const name = (id: number) => members.find((member) => member.id === id)?.name ?? `Member ${id}`
  const owner = assignment?.member_id
  const recommended = recommendation?.member_id ?? undefined
  const ineligible = recommendation?.ineligible ?? []
  const ineligibleIds = new Set(ineligible.map((item) => item.member_id))
  const canApprove = recommended !== undefined && recommended !== owner
  const done = task.status === 'done'

  const approve = () => {
    if (recommended === undefined) return
    apply.mutate(
      {
        items: [
          {
            task_id: task.id,
            member_id: recommended,
            source: 'ai',
            score_breakdown: toBreakdown(recommendation?.score),
          },
        ],
      },
      { onSuccess: onClose },
    )
  }

  const override = () => {
    const chosen = Number(memberId)
    const candidate = recommendation?.candidates.find((item) => item.member_id === chosen)
    apply.mutate(
      {
        items: [
          {
            task_id: task.id,
            member_id: chosen,
            source: 'pm_override',
            reason: reason.trim(),
            score_breakdown: toBreakdown(candidate?.score),
          },
        ],
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <p className="numeric text-xs text-muted-foreground">{formatTaskId(task.id)}</p>
          <SheetTitle>{task.title}</SheetTitle>
          <SheetDescription>
            {owner === undefined ? 'Unassigned' : `Owner: ${name(owner)}`}
            {recommendation ? (
              <>
                {' · '}
                {formatDate(recommendation.window_start)} to{' '}
                {formatDate(recommendation.window_end)}
              </>
            ) : null}
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-5 px-4 pb-6">
          {recommendation ? (
            <>
              <section>
                <h3 className="text-[15px] leading-5 font-semibold">Top candidates</h3>
                {recommendation.candidates.length === 0 ? (
                  <p className="mt-1 text-muted-foreground">No member is eligible for this task.</p>
                ) : (
                  <ul className="mt-2 flex flex-col gap-2">
                    {recommendation.candidates.map((candidate) => (
                      <CandidateCard
                        key={candidate.member_id}
                        candidate={candidate}
                        name={name(candidate.member_id)}
                        recommended={candidate.member_id === recommended}
                      />
                    ))}
                  </ul>
                )}
              </section>
              {ineligible.length > 0 ? (
                <details>
                  <summary className="cursor-pointer rounded-sm text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    {ineligible.length} not eligible
                  </summary>
                  <ul className="mt-2 flex flex-col gap-1">
                    {ineligible.map((item) => (
                      <li key={item.member_id}>
                        {name(item.member_id)}
                        <span className="block text-xs text-muted-foreground">{item.reason}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
              <ExplanationBlock projectId={projectId} taskId={task.id} mode={mode} />
            </>
          ) : (
            <p className="text-muted-foreground">Recommendations are loading.</p>
          )}

          {done ? (
            <p className="text-muted-foreground">This task is done, so its owner is final.</p>
          ) : overriding ? (
            <section className="flex flex-col gap-2">
              <label className="micro-label" htmlFor="override-member">
                Assign to
              </label>
              <select
                id="override-member"
                value={memberId}
                onChange={(event) => setMemberId(event.target.value)}
                className="h-8 rounded-lg border border-input bg-surface-2 px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="">Choose a member</option>
                {members
                  .filter((member) => member.id !== owner)
                  .map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.name}
                      {ineligibleIds.has(member.id) ? ' (not eligible)' : ''}
                    </option>
                  ))}
              </select>
              <label className="micro-label" htmlFor="override-reason">
                Reason
              </label>
              <Textarea
                id="override-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Why this member instead of the recommendation"
              />
              <div className="flex gap-2">
                <Button
                  disabled={!memberId || !reason.trim() || apply.isPending}
                  onClick={override}
                >
                  {apply.isPending ? 'Saving' : 'Save override'}
                </Button>
                <Button variant="ghost" onClick={() => setOverriding(false)}>
                  Cancel
                </Button>
              </div>
            </section>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Button disabled={!canApprove || apply.isPending} onClick={approve}>
                {apply.isPending
                  ? 'Saving'
                  : recommended !== undefined && recommended === owner
                    ? 'Already the owner'
                    : 'Approve'}
              </Button>
              <Button variant="outline" onClick={() => setOverriding(true)}>
                Override
              </Button>
            </div>
          )}
          {apply.isError ? <p className="text-danger">{apply.error.message}</p> : null}
        </div>
      </SheetContent>
    </Sheet>
  )
}
