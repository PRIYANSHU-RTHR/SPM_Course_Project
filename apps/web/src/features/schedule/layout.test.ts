import { describe, expect, it } from 'vitest'
import { initialViewport, layoutNetwork, NODE_HEIGHT, NODE_WIDTH } from './layout'

describe('layoutNetwork', () => {
  it('places a successor to the right of its predecessor', () => {
    const positions = layoutNetwork([1, 2, 3], [
      { pred: 1, succ: 2 },
      { pred: 2, succ: 3 },
    ])
    expect(positions.get(2)!.x).toBeGreaterThanOrEqual(positions.get(1)!.x + NODE_WIDTH)
    expect(positions.get(3)!.x).toBeGreaterThanOrEqual(positions.get(2)!.x + NODE_WIDTH)
  })

  it('does not overlap tasks in the same rank', () => {
    const positions = layoutNetwork([1, 2, 3], [
      { pred: 1, succ: 2 },
      { pred: 1, succ: 3 },
    ])
    const gap = Math.abs(positions.get(2)!.y - positions.get(3)!.y)
    expect(gap).toBeGreaterThanOrEqual(NODE_HEIGHT)
  })

  it('handles a task with no links', () => {
    expect(layoutNetwork([1], []).get(1)).toBeDefined()
  })
})

describe('initialViewport', () => {
  const size = { width: 1200, height: 600 }

  it('fits a small graph at no more than full size', () => {
    expect(initialViewport([{ x: 0, y: 0 }], size).zoom).toBe(1)
  })

  it('stops at a readable zoom and starts from the left edge of a wide graph', () => {
    const wide = [
      { x: 100, y: 0 },
      { x: 3000, y: 0 },
    ]
    const viewport = initialViewport(wide, size)
    expect(viewport.zoom).toBe(0.7)
    expect(viewport.x + 100 * viewport.zoom).toBe(16)
  })
})
