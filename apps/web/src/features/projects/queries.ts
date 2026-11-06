import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import type { Page, Project, ProjectFull } from '@/lib/api/provisional'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: ({ signal }) => apiFetch<Page<Project>>('/projects?limit=100', { signal }),
  })
}

export function useProjectFull(projectId: number | undefined) {
  return useQuery({
    queryKey: ['projects', projectId, 'full'],
    queryFn: ({ signal }) => apiFetch<ProjectFull>(`/projects/${projectId}/full`, { signal }),
    enabled: projectId !== undefined,
  })
}
