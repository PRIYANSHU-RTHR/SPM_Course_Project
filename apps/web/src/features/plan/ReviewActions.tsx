import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { PlanReview } from '@/lib/api/schemas'
import { type Edits, invalidTasks, toChanges } from './planModel'
import { useResumePlan } from './queries'

interface ReviewActionsProps {
  threadId: string
  review: PlanReview
  edits: Edits
  onDiscard: () => void
}

export function ReviewActions({ threadId, review, edits, onDiscard }: ReviewActionsProps) {
  const resume = useResumePlan(threadId)
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const changes = toChanges(review, edits)
  const invalid = invalidTasks(review, edits)
  const dirty = Object.keys(edits).length > 0

  if (rejecting) {
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor="reject-reason" className="micro-label">
          Why reject this plan
        </label>
        <Textarea
          id="reject-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. the brief changed; payments are out of scope for this term"
        />
        <div className="flex gap-2">
          <Button
            variant="destructive"
            disabled={!reason.trim() || resume.isPending}
            onClick={() => resume.mutate({ action: 'reject', reason: reason.trim() })}
          >
            Reject plan
          </Button>
          <Button variant="ghost" onClick={() => setRejecting(false)}>
            Cancel
          </Button>
        </div>
        {resume.isError ? <p className="text-danger">{resume.error.message}</p> : null}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          disabled={dirty || resume.isPending}
          onClick={() => resume.mutate({ action: 'approve' })}
        >
          Approve plan
        </Button>
        <Button
          variant="outline"
          disabled={changes.length === 0 || invalid.length > 0 || resume.isPending}
          onClick={() => resume.mutate({ action: 'edit', changes })}
        >
          Request changes{changes.length > 0 ? ` (${changes.length})` : ''}
        </Button>
        {dirty ? (
          <Button variant="ghost" onClick={onDiscard}>
            Discard edits
          </Button>
        ) : null}
        <Button variant="ghost" className="ml-auto" onClick={() => setRejecting(true)}>
          Reject
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        {invalid.length > 0
          ? `Fix the hours on ${invalid.join(', ')} first.`
          : dirty
            ? 'Send your edits to re-estimate, re-schedule and re-assign before approving.'
            : `Revision ${review.revision}. Approving creates the project with these tasks and owners.`}
      </p>
      {resume.isError ? <p className="text-danger">{resume.error.message}</p> : null}
    </div>
  )
}
