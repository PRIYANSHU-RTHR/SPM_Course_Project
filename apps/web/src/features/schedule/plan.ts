/** Joins the plan, CPM and schedule responses into one record per task. No scheduling logic here. */
import type {
  Epic,
  Member,
  ProjectCpm,
  ProjectFull,
  ProjectSchedule,
  Task,
} from '@/lib/api/schemas'

export interface PlanTask {
  id: number
  title: string
  epicId: number
  status: Task['status']
  hours: number
  es: number
  ef: number
  ls: number
  lf: number
  totalSlack: number
  freeSlack: number
  critical: boolean
  start: string
  end: string
  resourceDelayDays: number
  ownerId: number | undefined
  ownerName: string | undefined
  predecessors: number[]
  successors: number[]
}

export interface PlanEpic {
  epic: Epic
  tasks: PlanTask[]
}

export interface Plan {
  tasks: PlanTask[]
  byId: Map<number, PlanTask>
  epics: PlanEpic[]
  criticalEdges: Set<string>
  edges: { pred: number; succ: number }[]
  start: string
  finish: string
  deadline: string
}

export const edgeKey = (pred: number, succ: number) => `${pred}-${succ}`

/** Pairs of tasks that follow each other on a critical path. */
function criticalEdgeKeys(paths: number[][]): Set<string> {
  const keys = new Set<string>()
  for (const path of paths) {
    path.slice(1).forEach((succ, index) => keys.add(edgeKey(path[index], succ)))
  }
  return keys
}

export function buildPlan(
  full: ProjectFull,
  cpm: ProjectCpm,
  schedule: ProjectSchedule,
  members: Member[],
): Plan {
  const details = new Map(full.tasks.map((task) => [task.id, task]))
  const placed = new Map(schedule.tasks.map((task) => [task.task_id, task]))
  const names = new Map(members.map((member) => [member.id, member.name]))
  const predecessors = new Map<number, number[]>()
  const successors = new Map<number, number[]>()
  for (const { pred_task_id: pred, succ_task_id: succ } of full.dependencies) {
    predecessors.set(succ, [...(predecessors.get(succ) ?? []), pred])
    successors.set(pred, [...(successors.get(pred) ?? []), succ])
  }

  const tasks: PlanTask[] = []
  for (const row of cpm.tasks) {
    const task = details.get(row.task_id)
    const slot = placed.get(row.task_id)
    if (!task || !slot) continue
    const ownerId = slot.member_id ?? undefined
    tasks.push({
      id: task.id,
      title: task.title,
      epicId: task.epic_id,
      status: task.status,
      hours: row.duration_hours,
      es: row.es,
      ef: row.ef,
      ls: row.ls,
      lf: row.lf,
      totalSlack: row.total_slack,
      freeSlack: row.free_slack,
      critical: row.critical,
      start: slot.start,
      end: slot.end,
      resourceDelayDays: slot.resource_delay_days,
      ownerId,
      ownerName: ownerId === undefined ? undefined : names.get(ownerId),
      predecessors: predecessors.get(task.id) ?? [],
      successors: successors.get(task.id) ?? [],
    })
  }

  const byId = new Map(tasks.map((task) => [task.id, task]))
  const epics = [...full.epics]
    .sort((a, b) => a.position - b.position)
    .map((epic) => ({
      epic,
      tasks: tasks
        .filter((task) => task.epicId === epic.id)
        .sort((a, b) => a.start.localeCompare(b.start) || a.id - b.id),
    }))
    .filter((group) => group.tasks.length > 0)

  return {
    tasks,
    byId,
    epics,
    criticalEdges: criticalEdgeKeys(cpm.critical_paths),
    edges: full.dependencies
      .filter((dep) => byId.has(dep.pred_task_id) && byId.has(dep.succ_task_id))
      .map((dep) => ({ pred: dep.pred_task_id, succ: dep.succ_task_id })),
    start: schedule.start,
    finish: schedule.finish,
    deadline: schedule.deadline,
  }
}
