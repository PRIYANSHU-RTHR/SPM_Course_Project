import { useMemo, useState } from 'react'
import { Panel, PanelEmpty } from '@/components/Panel'
import type { Member, ProjectFull, ProjectSchedule } from '@/lib/api/schemas'
import { isoWeek } from '@/lib/dates'
import { formatPercent, formatShortDate, formatTaskId } from '@/lib/format'
import { cn } from '@/lib/utils'
import { heatShare, loadKey, loadsByCell, weekStarts, weekTasks } from './teamMetrics'

interface CapacityHeatmapProps {
  members: Member[]
  schedule: ProjectSchedule
  full: ProjectFull
}

export function CapacityHeatmap({ members, schedule, full }: CapacityHeatmapProps) {
  const weeks = useMemo(() => weekStarts(schedule.loads), [schedule.loads])
  const cells = useMemo(() => loadsByCell(schedule.loads), [schedule.loads])
  const [selected, setSelected] = useState<{ memberId: number; week: string } | null>(null)
  const titles = new Map(full.tasks.map((task) => [task.id, task.title]))
  const selectedName = members.find((member) => member.id === selected?.memberId)?.name
  const tasks = selected ? weekTasks(schedule.tasks, selected.memberId, selected.week) : []

  if (weeks.length === 0) {
    return (
      <Panel title="Capacity">
        <PanelEmpty>No work is scheduled yet.</PanelEmpty>
      </Panel>
    )
  }

  return (
    <Panel title="Capacity">
      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-0 [&_thead_th]:border-b">
          <thead>
            <tr className="bg-surface-2">
              <th className="micro-label sticky left-0 z-10 bg-surface-2 px-4 py-2 text-left font-normal">
                Member
              </th>
              {weeks.map((week) => (
                <th
                  key={week}
                  title={`Week of ${formatShortDate(week)}`}
                  className="micro-label px-0.5 py-2 text-center font-normal"
                >
                  W{isoWeek(week)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-surface px-4 py-0.5 text-left font-normal whitespace-nowrap"
                >
                  {member.name}
                </th>
                {weeks.map((week) => {
                  const load = cells.get(loadKey(member.id, week))
                  const value = load?.utilisation ?? 0
                  const isSelected = selected?.memberId === member.id && selected.week === week
                  return (
                    <td key={week} className="px-0.5 py-0.5">
                      <button
                        type="button"
                        disabled={value === 0}
                        aria-pressed={isSelected}
                        aria-label={`${member.name}, week ${isoWeek(week)}, ${formatPercent(value)} utilised`}
                        onClick={() =>
                          setSelected(isSelected ? null : { memberId: member.id, week })
                        }
                        className={cn(
                          'numeric h-7 w-full min-w-11 rounded-sm text-[11px] outline-none transition-colors duration-150 ease-out enabled:cursor-pointer focus-visible:ring-2 focus-visible:ring-ring disabled:text-subtle',
                          value > 1 && 'ring-1 ring-danger',
                          isSelected && 'ring-2 ring-brand',
                        )}
                        style={{
                          background: `color-mix(in srgb, var(--accent) ${heatShare(value)}%, var(--surface-2))`,
                        }}
                      >
                        {formatPercent(value)}
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected ? (
        <div className="border-t px-4 py-3">
          <p className="micro-label">
            {selectedName} · W{isoWeek(selected.week)}
          </p>
          {tasks.length === 0 ? (
            <p className="mt-1 text-muted-foreground">No tasks this week.</p>
          ) : (
            <ul className="mt-1">
              {tasks.map((task) => (
                <li key={task.task_id} className="flex gap-2 py-0.5">
                  <span className="numeric shrink-0 text-muted-foreground">
                    {formatTaskId(task.task_id)}
                  </span>
                  <span className="min-w-0 truncate">{titles.get(task.task_id)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </Panel>
  )
}
