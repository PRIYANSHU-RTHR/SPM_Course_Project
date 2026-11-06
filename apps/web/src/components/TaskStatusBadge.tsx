import { Badge } from '@/components/ui/badge'
import type { TaskStatus } from '@/lib/api/schemas'

type StatusStyle = { label: string; variant: 'outline' | 'secondary' | 'success' | 'warning' }

const STATUS: Record<TaskStatus, StatusStyle> = {
  todo: { label: 'Todo', variant: 'outline' },
  in_progress: { label: 'In progress', variant: 'secondary' },
  blocked: { label: 'Blocked', variant: 'warning' },
  done: { label: 'Done', variant: 'success' },
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return <Badge variant={STATUS[status].variant}>{STATUS[status].label}</Badge>
}
