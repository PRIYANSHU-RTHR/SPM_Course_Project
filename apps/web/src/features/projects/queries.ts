import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import type {
  AppliedAssignment,
  ApplyRequest,
  Explanation,
  MemberPage,
  ProjectCpm,
  ProjectEvm,
  ProjectForecast,
  ProjectFull,
  ProjectPage,
  ProjectSchedule,
  RecommendResponse,
  Risk,
  RiskPage,
  RiskRefreshResult,
} from '@/lib/api/schemas'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: ({ signal }) => apiFetch<ProjectPage>('/projects?limit=100', { signal }),
  })
}

export function useMembers() {
  return useQuery({
    queryKey: ['members'],
    queryFn: ({ signal }) => apiFetch<MemberPage>('/members?limit=200', { signal }),
  })
}

function useProjectResource<T>(projectId: number | undefined, resource: string) {
  return useQuery({
    queryKey: ['projects', projectId, resource],
    queryFn: ({ signal }) => apiFetch<T>(`/projects/${projectId}/${resource}`, { signal }),
    enabled: projectId !== undefined,
  })
}

export const useProjectFull = (id: number | undefined) =>
  useProjectResource<ProjectFull>(id, 'full')
export const useForecast = (id: number | undefined) =>
  useProjectResource<ProjectForecast>(id, 'forecast')
export const useEvm = (id: number | undefined) => useProjectResource<ProjectEvm>(id, 'evm')
export const useCpm = (id: number | undefined) => useProjectResource<ProjectCpm>(id, 'cpm')
export const useSchedule = (id: number | undefined) =>
  useProjectResource<ProjectSchedule>(id, 'schedule')
export const useRisks = (id: number | undefined) =>
  useProjectResource<RiskPage>(id, 'risks?limit=200')

export type AssignmentMode = 'greedy' | 'optimal'

export function useRecommendations(projectId: number | undefined, mode: AssignmentMode) {
  return useQuery({
    queryKey: ['projects', projectId, 'recommend', mode],
    queryFn: ({ signal }) =>
      apiFetch<RecommendResponse>(`/projects/${projectId}/assignments/recommend?mode=${mode}`, {
        method: 'POST',
        signal,
      }),
    enabled: projectId !== undefined,
  })
}

export function useExplanation(projectId: number, taskId: number, mode: AssignmentMode) {
  return useQuery({
    queryKey: ['projects', projectId, 'explain', taskId, mode],
    queryFn: ({ signal }) =>
      apiFetch<Explanation>(`/projects/${projectId}/assignments/${taskId}/explain?mode=${mode}`, {
        signal,
      }),
    retry: false,
  })
}

export function useApplyAssignment(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ApplyRequest) =>
      apiFetch<AppliedAssignment[]>(`/projects/${projectId}/assignments/apply`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects', projectId] }),
  })
}

export function useGenerateRiskPlan(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (riskId: number) =>
      apiFetch<Risk>(`/projects/${projectId}/risks/${riskId}/plan`, { method: 'POST' }),
    onSuccess: (risk) =>
      queryClient.setQueryData<RiskPage>(['projects', projectId, 'risks?limit=200'], (page) =>
        page
          ? { ...page, items: page.items.map((item) => (item.id === risk.id ? risk : item)) }
          : page,
      ),
  })
}

export function useRefreshRisks(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<RiskRefreshResult>(`/projects/${projectId}/risks/refresh`, { method: 'POST' }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'risks?limit=200'] }),
  })
}
