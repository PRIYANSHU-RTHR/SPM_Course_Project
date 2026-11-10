/** Left-to-right graph layout. Returns the top-left corner of each node. */
import dagre from '@dagrejs/dagre'

export const NODE_WIDTH = 192
export const NODE_HEIGHT = 80

export function layoutNetwork(
  ids: number[],
  edges: { pred: number; succ: number }[],
): Map<number, { x: number; y: number }> {
  const graph = new dagre.graphlib.Graph()
  graph.setGraph({ rankdir: 'LR', ranksep: 36, nodesep: 14, marginx: 8, marginy: 8 })
  graph.setDefaultEdgeLabel(() => ({}))
  for (const id of ids) graph.setNode(String(id), { width: NODE_WIDTH, height: NODE_HEIGHT })
  for (const { pred, succ } of edges) graph.setEdge(String(pred), String(succ))
  dagre.layout(graph)

  return new Map(
    ids.map((id) => {
      const { x, y } = graph.node(String(id))
      return [id, { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 }]
    }),
  )
}

/** Fits the graph when that stays readable; otherwise opens at `minZoom` from the left edge. */
export function initialViewport(
  nodes: { x: number; y: number }[],
  size: { width: number; height: number },
  minZoom = 0.7,
) {
  const right = Math.max(...nodes.map((node) => node.x + NODE_WIDTH))
  const left = Math.min(...nodes.map((node) => node.x))
  const top = Math.min(...nodes.map((node) => node.y))
  const bottom = Math.max(...nodes.map((node) => node.y + NODE_HEIGHT))
  const padding = 16
  const fit = Math.min(
    (size.width - padding * 2) / (right - left),
    (size.height - padding * 2) / (bottom - top),
    1,
  )
  const zoom = Math.max(fit, minZoom)
  return {
    zoom,
    x: padding - left * zoom,
    y: Math.max((size.height - (bottom - top) * zoom) / 2, padding) - top * zoom,
  }
}
