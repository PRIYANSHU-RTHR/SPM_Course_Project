import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { type AssignmentMode, useExplanation } from '@/features/projects/queries'
import { ApiError } from '@/lib/api/client'

interface ExplanationBlockProps {
  projectId: number
  taskId: number
  mode: AssignmentMode
}

export function ExplanationBlock({ projectId, taskId, mode }: ExplanationBlockProps) {
  const explanation = useExplanation(projectId, taskId, mode)
  const data = explanation.data
  const unavailable =
    explanation.error instanceof ApiError &&
    explanation.error.status === 404 &&
    explanation.error.code === 'unknown_error'

  return (
    <section>
      <div className="flex items-center gap-2">
        <p className="micro-label">Gemini · explanation</p>
        {data ? (
          <Badge variant="outline">{data.source === 'model' ? 'grounded' : 'template'}</Badge>
        ) : null}
      </div>
      {explanation.isLoading ? (
        <Skeleton className="mt-2 h-12 w-full" />
      ) : data ? (
        <p className="mt-1">{data.text}</p>
      ) : (
        <p className="mt-1 text-muted-foreground">
          {unavailable
            ? 'Explanations are not available on this API yet. The numbers above come from the engine.'
            : explanation.error?.message}
        </p>
      )}
    </section>
  )
}
