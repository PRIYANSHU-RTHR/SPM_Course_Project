import { Handle, type Node, type NodeProps, Position } from '@xyflow/react'
import { memo } from 'react'
import { OwnerChip } from '@/components/OwnerChip'
import { formatHours, formatTaskId } from '@/lib/format'
import { cn } from '@/lib/utils'
import { NODE_HEIGHT, NODE_WIDTH } from './layout'
import type { PlanTask } from './plan'

export type TaskNodeData = Node<{ task: PlanTask }, 'task'>

const HANDLE = '!size-px !min-h-0 !min-w-0 !border-0 !bg-transparent'

export const TaskNode = memo(function TaskNode({ data }: NodeProps<TaskNodeData>) {
  const { task } = data
  return (
    <div
      className={cn(
        'flex cursor-pointer flex-col justify-between rounded-xl border bg-surface px-3 py-2 transition-colors duration-150 ease-out hover:bg-surface-2',
        task.critical ? 'border-brand' : 'border-border-strong',
      )}
      style={{ width: NODE_WIDTH, height: NODE_HEIGHT }}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} className={HANDLE} />
      <div className="flex items-center justify-between gap-2">
        <span className="numeric text-xs text-muted-foreground">{formatTaskId(task.id)}</span>
        {task.ownerId !== undefined && task.ownerName ? (
          <OwnerChip id={task.ownerId} name={task.ownerName} />
        ) : (
          <span className="text-xs text-subtle">Unassigned</span>
        )}
      </div>
      <p className="truncate text-[13px] leading-[18px]">{task.title}</p>
      <p className="numeric text-[11px] leading-4 text-muted-foreground">
        Te {formatHours(task.hours)} · slack {formatHours(task.totalSlack)}
      </p>
      <Handle type="source" position={Position.Right} isConnectable={false} className={HANDLE} />
    </div>
  )
})
