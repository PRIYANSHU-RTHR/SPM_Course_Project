import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import type {
  MemberPage,
  ProjectCpm,
  ProjectEvm,
  ProjectForecast,
  ProjectFull,
  ProjectPage,
  ProjectSchedule,
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

export function useRefreshRisks(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<RiskRefreshResult>(`/projects/${projectId}/risks/refresh`, { method: 'POST' }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'risks?limit=200'] }),
  })
}
