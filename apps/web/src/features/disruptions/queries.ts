import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import type {
  AdvanceResult,
  AuditPage,
  Disruption,
  DisruptionStarted,
  ProjectMetrics,
  ProposalPage,
  ResumeAccepted,
} from '@/lib/api/schemas'

export const AUDIT_PAGE = 30

export function useMetrics(projectId: number | undefined) {
  return useQuery({
    queryKey: ['projects', projectId, 'metrics'],
    queryFn: ({ signal }) => apiFetch<ProjectMetrics>(`/projects/${projectId}/metrics`, { signal }),
    enabled: projectId !== undefined,
  })
}

export function useProposals(projectId: number | undefined) {
  return useQuery({
    queryKey: ['projects', projectId, 'proposals'],
    queryFn: ({ signal }) =>
      apiFetch<ProposalPage>(`/projects/${projectId}/proposals?limit=20`, { signal }),
    enabled: projectId !== undefined,
  })
}

/** Everything the project's pages show can change after a disruption, decision or clock move. */
function useRefreshProject(projectId: number) {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: ['projects', projectId] })
}

export function useCreateDisruption(projectId: number) {
  return useMutation({
    mutationFn: (body: Disruption) =>
      apiFetch<DisruptionStarted>(`/projects/${projectId}/disruptions`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useAdvanceClock(projectId: number) {
  const refresh = useRefreshProject(projectId)
  return useMutation({
    mutationFn: (days: number) =>
      apiFetch<AdvanceResult>(`/projects/${projectId}/simulate/advance?days=${days}`, {
        method: 'POST',
      }),
    onSuccess: () => refresh(),
  })
}

export type ProposalDecision =
  | { action: 'approve'; reason?: string }
  | { action: 'reject'; reason: string }

export function useDecideProposal(projectId: number) {
  const refresh = useRefreshProject(projectId)
  return useMutation({
    mutationFn: ({ threadId, decision }: { threadId: string; decision: ProposalDecision }) =>
      apiFetch<ResumeAccepted>(`/workflows/${threadId}/resume`, {
        method: 'POST',
        body: JSON.stringify(decision),
      }),
    onSuccess: () => refresh(),
  })
}

export function useAudit(projectId: number | undefined) {
  return useInfiniteQuery({
    queryKey: ['projects', projectId, 'audit'],
    queryFn: ({ pageParam, signal }) =>
      apiFetch<AuditPage>(`/projects/${projectId}/audit?limit=${AUDIT_PAGE}&offset=${pageParam}`, {
        signal,
      }),
    initialPageParam: 0,
    getNextPageParam: (last) =>
      last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined,
    enabled: projectId !== undefined,
  })
}
