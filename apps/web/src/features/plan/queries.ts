import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import type {
  ApproveDecision,
  EditDecision,
  PlanExample,
  PlanStart,
  PlanStarted,
  RejectDecision,
  ResumeAccepted,
  SkillPage,
  WorkflowState,
} from '@/lib/api/schemas'

export const workflowKey = (threadId: string) => ['workflows', threadId] as const

export function usePlanExample() {
  return useQuery({
    queryKey: ['workflows', 'plan-example'],
    queryFn: ({ signal }) => apiFetch<PlanExample>('/workflows/plan/example', { signal }),
    enabled: false, // fetched when the PM asks for the demo brief
    staleTime: Infinity,
  })
}

export function useStartPlan() {
  return useMutation({
    mutationFn: (body: PlanStart) =>
      apiFetch<PlanStarted>('/workflows/plan', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useWorkflowState(threadId: string) {
  return useQuery({
    queryKey: workflowKey(threadId),
    queryFn: ({ signal }) => apiFetch<WorkflowState>(`/workflows/${threadId}/state`, { signal }),
  })
}

export type Decision = ApproveDecision | EditDecision | RejectDecision

export function useResumePlan(threadId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (decision: Decision) =>
      apiFetch<ResumeAccepted>(`/workflows/${threadId}/resume`, {
        method: 'POST',
        body: JSON.stringify(decision),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workflowKey(threadId) }),
  })
}

export function useSkills() {
  return useQuery({
    queryKey: ['skills'],
    queryFn: ({ signal }) => apiFetch<SkillPage>('/skills?limit=200', { signal }),
    staleTime: 5 * 60_000,
  })
}
