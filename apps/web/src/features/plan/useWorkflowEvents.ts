import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { API_URL } from '@/lib/api/client'
import type { WorkflowEvent } from '@/lib/api/schemas'
import { mergeEvents, TERMINAL } from './planModel'
import { workflowKey } from './queries'

interface Received {
  threadId: string
  events: WorkflowEvent[]
  disconnected: boolean
}

/**
 * Live events of one workflow run (SSE). Past events are replayed first, so a reload rebuilds
 * the timeline. Every `run` event refetches the run state; a terminal one closes the stream
 * (otherwise the browser would reconnect forever).
 */
export function useWorkflowEvents(
  threadId: string | undefined,
  /** Called on every `run` event (status change), e.g. to refetch related data. */
  onRun?: (event: WorkflowEvent) => void,
) {
  const queryClient = useQueryClient()
  const onRunRef = useRef(onRun)
  useEffect(() => {
    onRunRef.current = onRun
  })
  const [received, setReceived] = useState<Received>({
    threadId: threadId ?? '',
    events: [],
    disconnected: false,
  })

  useEffect(() => {
    if (!threadId) return undefined
    const source = new EventSource(`${API_URL}/workflows/${threadId}/events`)
    // Events for another thread (after navigating) are dropped, not merged.
    const update = (change: (current: Received) => Partial<Received>) =>
      setReceived((current) => {
        const base =
          current.threadId === threadId ? current : { threadId, events: [], disconnected: false }
        return { ...base, ...change(base) }
      })

    const onEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as WorkflowEvent
      update((current) => ({ events: mergeEvents(current.events, [event]) }))
      if (event.type === 'run') {
        void queryClient.invalidateQueries({ queryKey: workflowKey(threadId) })
        onRunRef.current?.(event)
        if (event.status && TERMINAL.has(event.status)) source.close()
      }
    }
    source.addEventListener('node', onEvent)
    source.addEventListener('run', onEvent)
    source.onopen = () => update(() => ({ disconnected: false }))
    source.onerror = () =>
      update(() => ({ disconnected: source.readyState === EventSource.CLOSED }))

    return () => source.close()
  }, [threadId, queryClient])

  const current = received.threadId === threadId
  return {
    events: current ? received.events : [],
    disconnected: current ? received.disconnected : false,
  }
}
