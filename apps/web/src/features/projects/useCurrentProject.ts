import { useEffect } from 'react'
import { useMatch } from 'react-router'
import { useProjects } from './queries'

const STORAGE_KEY = 'orchestrai.project'

function readStoredId(): number | undefined {
  try {
    const stored = Number(localStorage.getItem(STORAGE_KEY))
    return Number.isInteger(stored) && stored > 0 ? stored : undefined
  } catch {
    return undefined
  }
}

function storeId(id: number) {
  try {
    localStorage.setItem(STORAGE_KEY, String(id))
  } catch {
    // Storage can be blocked; the switcher still works for this page.
  }
}

/** The project in the URL, else the last one opened, else the first one in the list. */
export function useCurrentProject() {
  const match = useMatch('/projects/:projectId/*')
  const query = useProjects()
  const projects = query.data?.items ?? []

  const routeId = Number(match?.params.projectId)
  const fromRoute = projects.find((item) => item.id === routeId)
  const stored = projects.find((item) => item.id === readStoredId())
  const project = fromRoute ?? stored ?? projects[0]

  useEffect(() => {
    if (fromRoute) storeId(fromRoute.id)
  }, [fromRoute])

  return {
    project,
    projectId: project?.id,
    projects,
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
