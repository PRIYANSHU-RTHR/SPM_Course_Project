import { describe, expect, it } from 'vitest'
import type { PlanReview, WorkflowEvent } from '@/lib/api/schemas'
import {
  buildTimeline,
  estimateError,
  invalidTasks,
  lastStatus,
  mergeEvents,
  toChanges,
} from './planModel'

let seq = 0
function node(name: string, phase: 'start' | 'end', summary = '', ms = 12): WorkflowEvent {
  seq += 1
  return {
    seq,
    thread_id: 't',
    type: 'node',
    node: name,
    phase,
    summary,
    duration_ms: phase === 'end' ? ms : null,
  }
}
function run(status: WorkflowEvent['status']): WorkflowEvent {
  seq += 1
  return { seq, thread_id: 't', type: 'run', status, summary: '' }
}

const REVIEW = {
  wbs: {
    epics: [
      {
        local_id: 'E-1',
        title: 'Ordering',
        tasks: [
          {
            local_id: 'T-001',
            title: 'Menu API',
            description: '',
            o: 8,
            m: 12,
            p: 20,
            required_skills: [{ skill: 'python', level: 3, must: true }],
            predecessors: [],
          },
          {
            local_id: 'T-002',
            title: 'Cart screen',
            description: '',
            o: 4,
            m: 6,
            p: 10,
            required_skills: [],
            predecessors: ['T-001'],
          },
        ],
      },
    ],
    assumptions: [],
  },
} as unknown as PlanReview

describe('timeline', () => {
  it('pairs start and end per node and marks the review as waiting', () => {
    seq = 0
    const events = [
      run('running'),
      node('decompose', 'start'),
      node('decompose', 'end', '25 tasks in 5 epics', 840),
      node('estimate', 'start'),
      node('estimate', 'end', 'total te 341.7 h'),
      node('pm_review', 'start'),
      node('pm_review', 'end', 'waiting for PM review'),
      run('waiting'),
    ]
    const steps = buildTimeline(events)

    expect(steps.map((s) => [s.label, s.state])).toEqual([
      ['Decompose brief', 'done'],
      ['Estimate', 'done'],
      ['PM review', 'waiting'],
    ])
    expect(steps[0]).toMatchObject({ durationMs: 840, summary: '25 tasks in 5 epics' })
    expect(lastStatus(events)).toBe('waiting')
  })

  it('keeps one row per run of a node after an edit, and fails open rows', () => {
    seq = 0
    const steps = buildTimeline([
      node('estimate', 'start'),
      node('estimate', 'end', 'first'),
      node('estimate', 'start'),
      node('estimate', 'end', 'second'),
      node('commit', 'start'),
      run('failed'),
    ])
    expect(steps.map((s) => s.summary)).toEqual(['first', 'second', ''])
    expect(steps[2]?.state).toBe('failed')
    expect(new Set(steps.map((s) => s.key)).size).toBe(3)
  })

  it('merges replayed events once, in seq order', () => {
    seq = 0
    const a = node('decompose', 'start')
    const b = node('decompose', 'end')
    expect(mergeEvents([b], [a, b]).map((e) => e.seq)).toEqual([1, 2])
  })
})

describe('edits', () => {
  it('validates estimates like the API', () => {
    expect(estimateError(8, 12, 20)).toBeNull()
    expect(estimateError(12, 8, 20)).toMatch(/o ≤ m ≤ p/)
    expect(estimateError(0.5, 1, 2)).not.toBeNull()
    expect(estimateError(8, 12, 81)).not.toBeNull()
    expect(estimateError(Number.NaN, 1, 2)).toMatch(/Enter hours/)
  })

  it('sends only real changes, in WBS order', () => {
    const changes = toChanges(REVIEW, {
      'T-002': { o: 4, m: 8 }, // o unchanged
      'T-001': { required_skills: [{ skill: 'python', level: 3, must: true }] }, // unchanged
    })
    expect(changes).toEqual([{ op: 'update', task_id: 'T-002', m: 8 }])
  })

  it('reports tasks whose edited hours break the rule', () => {
    expect(invalidTasks(REVIEW, { 'T-001': { p: 10 } })).toEqual(['T-001'])
    expect(invalidTasks(REVIEW, { 'T-001': { p: 30 } })).toEqual([])
  })
})
