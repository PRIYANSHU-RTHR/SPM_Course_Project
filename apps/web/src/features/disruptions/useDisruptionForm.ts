import type { FormEvent } from 'react'
import type { Disruption, Member, ProjectFull } from '@/lib/api/schemas'
import { useCreateDisruption } from './queries'

export const SELECT =
  'h-8 w-full rounded-lg border border-input bg-surface-2 px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring'

export interface FormProps {
  projectId: number
  /** The project's simulated "today"; dates default from it. */
  today: string
  full: ProjectFull
  members: Member[]
  /** A run is already waiting for a decision: new disruptions are refused (409). */
  blocked: boolean
  onStarted: (threadId: string) => void
}

export function useSubmit({ projectId, onStarted }: Pick<FormProps, 'projectId' | 'onStarted'>) {
  const create = useCreateDisruption(projectId)
  const submit = (body: Disruption) => (event: FormEvent) => {
    event.preventDefault()
    create.mutate(body, { onSuccess: ({ thread_id }) => onStarted(thread_id) })
  }
  return { create, submit }
}
