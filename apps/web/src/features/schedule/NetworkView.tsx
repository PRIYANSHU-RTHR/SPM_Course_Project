import '@xyflow/react/dist/base.css'
import { Controls, type Edge, MarkerType, ReactFlow } from '@xyflow/react'
import { useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { initialViewport, layoutNetwork } from './layout'
import { edgeKey, type Plan } from './plan'
import { TaskNode, type TaskNodeData } from './TaskNode'

const NODE_TYPES = { task: TaskNode }

function toGraph(plan: Plan, criticalOnly: boolean) {
  const tasks = criticalOnly ? plan.tasks.filter((task) => task.critical) : plan.tasks
  const ids = new Set(tasks.map((task) => task.id))
  const links = plan.edges.filter(
    ({ pred, succ }) =>
      ids.has(pred) &&
      ids.has(succ) &&
      (!criticalOnly || plan.criticalEdges.has(edgeKey(pred, succ))),
  )
  const positions = layoutNetwork(
    tasks.map((task) => task.id),
    links,
  )

  const nodes: TaskNodeData[] = tasks.map((task) => ({
    id: String(task.id),
    type: 'task',
    position: positions.get(task.id) ?? { x: 0, y: 0 },
    data: { task },
    draggable: false,
    connectable: false,
    ariaLabel: `Task ${task.id}: ${task.title}`,
  }))

  const edges: Edge[] = links.map(({ pred, succ }) => {
    const critical = plan.criticalEdges.has(edgeKey(pred, succ))
    const colour = critical ? 'var(--accent)' : 'var(--border-strong)'
    return {
      id: edgeKey(pred, succ),
      source: String(pred),
      target: String(succ),
      type: 'smoothstep',
      zIndex: critical ? 1 : 0,
      style: { stroke: colour, strokeWidth: critical ? 2 : 1 },
      markerEnd: { type: MarkerType.ArrowClosed, color: colour, width: 16, height: 16 },
    }
  })

  return { nodes, edges }
}

interface NetworkViewProps {
  plan: Plan
  onSelect: (taskId: number) => void
}

export function NetworkView({ plan, onSelect }: NetworkViewProps) {
  const [criticalOnly, setCriticalOnly] = useState(false)
  const { nodes, edges } = useMemo(() => toGraph(plan, criticalOnly), [plan, criticalOnly])
  const canvas = useRef<HTMLDivElement>(null)

  return (
    <div className="schedule-flow rounded-xl border bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-2">
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <li className="flex items-center gap-2">
            <span aria-hidden className="w-4 border-t-2 border-brand" />
            Critical path
          </li>
          <li className="flex items-center gap-2">
            <span aria-hidden className="w-4 border-t border-border-strong" />
            Other dependency
          </li>
        </ul>
        <Button
          variant={criticalOnly ? 'secondary' : 'outline'}
          size="sm"
          aria-pressed={criticalOnly}
          onClick={() => setCriticalOnly((value) => !value)}
        >
          Critical path only
        </Button>
      </div>
      <div ref={canvas} className="h-[480px] md:h-[600px]">
        <ReactFlow
          key={criticalOnly ? 'critical' : 'all'}
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          colorMode="dark"
          onInit={(flow) => {
            const size = canvas.current?.getBoundingClientRect()
            if (size) void flow.setViewport(initialViewport(nodes.map((n) => n.position), size))
          }}
          fitViewOptions={{ padding: 0.04 }}
          minZoom={0.2}
          maxZoom={1.5}
          nodesDraggable={false}
          nodesConnectable={false}
          edgesFocusable={false}
          zoomOnScroll={false}
          preventScrolling={false}
          onNodeClick={(_, node) => onSelect(Number(node.id))}
        >
          <Controls showInteractive={false} position="bottom-left" />
        </ReactFlow>
      </div>
    </div>
  )
}
