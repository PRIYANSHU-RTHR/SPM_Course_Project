import { http, HttpResponse } from 'msw'
import { API_URL } from '../client'
import type { Page, ProjectFull } from '../provisional'
import { assignments, dependencies, epics, members, projects, skills, tasks } from './data'

function paginate<T>(items: T[], request: Request): Page<T> {
  const params = new URL(request.url).searchParams
  const limit = Number(params.get('limit') ?? 50)
  const offset = Number(params.get('offset') ?? 0)
  return { items: items.slice(offset, offset + limit), total: items.length, limit, offset }
}

function notFound(id: string) {
  return HttpResponse.json(
    { error: { code: 'not_found', message: `Project ${id} not found`, details: {} } },
    { status: 404 },
  )
}

const url = (path: string) => `${API_URL}${path}`

/** Read endpoints from the Step 05 brief. Later steps add their own handlers here. */
export const handlers = [
  http.get(url('/health'), () => HttpResponse.json({ status: 'ok', version: 'mock' })),
  http.get(url('/projects'), ({ request }) => HttpResponse.json(paginate(projects, request))),
  http.get(url('/members'), ({ request }) => HttpResponse.json(paginate(members, request))),
  http.get(url('/skills'), ({ request }) => HttpResponse.json(paginate(skills, request))),
  http.get(url('/projects/:id'), ({ params }) => {
    const project = projects.find((item) => String(item.id) === params.id)
    return project ? HttpResponse.json(project) : notFound(String(params.id))
  }),
  http.get(url('/projects/:id/full'), ({ params }) => {
    const project = projects.find((item) => String(item.id) === params.id)
    if (!project) return notFound(String(params.id))
    const projectTasks = tasks.filter((task) => task.project_id === project.id)
    const taskIds = new Set(projectTasks.map((task) => task.id))
    const full: ProjectFull = {
      ...project,
      epics: epics.filter((epic) => epic.project_id === project.id),
      tasks: projectTasks,
      dependencies: dependencies.filter((dep) => taskIds.has(dep.succ_task_id)),
      assignments: assignments.filter((item) => taskIds.has(item.task_id)),
    }
    return HttpResponse.json(full)
  }),
]
