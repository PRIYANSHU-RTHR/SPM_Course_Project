import { TriangleAlert } from 'lucide-react'
import { Panel } from '@/components/Panel'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { Member } from '@/lib/api/schemas'
import { cn } from '@/lib/utils'
import { busFactorSkills, levelOf, skillNames } from './teamMetrics'

const LEVELS = [1, 2, 3, 4, 5]

function LevelSquares({ skill, level }: { skill: string; level: number }) {
  return (
    <span role="img" aria-label={`${skill} level ${level}`} className="inline-flex gap-px">
      {LEVELS.map((step) => (
        <span
          key={step}
          className={cn('size-1.5', step <= level ? 'bg-brand' : 'bg-border')}
        />
      ))}
    </span>
  )
}

export function SkillsMatrix({ members }: { members: Member[] }) {
  const skills = skillNames(members)
  const risky = busFactorSkills(members)

  return (
    <Panel title="Skills matrix">
      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-0 [&_tbody_tr:not(:last-child)>*]:border-b [&_thead_th]:border-b">
          <thead>
            <tr className="bg-surface-2">
              <th className="micro-label sticky left-0 z-10 bg-surface-2 px-4 py-2 text-left font-normal">
                Member
              </th>
              {skills.map((skill) => (
                <th key={skill} className="micro-label px-2 py-2 text-left font-normal normal-case">
                  <span className="flex items-center gap-1 whitespace-nowrap">
                    {skill}
                    {risky.has(skill) ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            aria-label={`Bus factor: only ${risky.get(skill)} is level 4 or above in ${skill}`}
                            className="rounded-sm text-warning outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            <TriangleAlert className="size-3" strokeWidth={1.5} />
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>
                          Only {risky.get(skill)} is level 4 or above
                        </TooltipContent>
                      </Tooltip>
                    ) : null}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-surface px-4 py-2 text-left font-normal whitespace-nowrap"
                >
                  {member.name}
                </th>
                {skills.map((skill) => (
                  <td key={skill} className="px-2 py-2">
                    <LevelSquares skill={skill} level={levelOf(member, skill)} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
