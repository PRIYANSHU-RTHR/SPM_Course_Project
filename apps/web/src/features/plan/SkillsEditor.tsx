import { X } from 'lucide-react'
import type { SkillReq } from '@/lib/api/schemas'

const LEVELS = [1, 2, 3, 4, 5]
const SELECT =
  'h-6 rounded-md border border-input bg-surface-2 px-1 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring'

interface SkillsEditorProps {
  taskId: string
  skills: SkillReq[]
  vocabulary: string[]
  onChange: (skills: SkillReq[]) => void
}

/** Required skills as chips: change the level, remove one, or add one from the team's skills. */
export function SkillsEditor({ taskId, skills, vocabulary, onChange }: SkillsEditorProps) {
  const used = new Set(skills.map((s) => s.skill))
  const addable = vocabulary.filter((name) => !used.has(name))

  return (
    <div className="flex flex-wrap items-center gap-1">
      {skills.map((req) => (
        <span
          key={req.skill}
          className="inline-flex items-center gap-1 rounded-md border bg-surface-2 py-0.5 pr-0.5 pl-1.5 text-xs"
        >
          <span className="font-mono">{req.skill}</span>
          <select
            aria-label={`${taskId} ${req.skill} level`}
            className={SELECT}
            value={req.level}
            onChange={(e) =>
              onChange(
                skills.map((s) =>
                  s.skill === req.skill ? { ...s, level: Number(e.target.value) } : s,
                ),
              )
            }
          >
            {LEVELS.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
          <button
            type="button"
            aria-label={`Remove ${req.skill} from ${taskId}`}
            className="rounded-sm p-0.5 text-subtle outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => onChange(skills.filter((s) => s.skill !== req.skill))}
          >
            <X className="size-3" strokeWidth={1.5} />
          </button>
        </span>
      ))}
      {addable.length > 0 ? (
        <select
          aria-label={`Add a skill to ${taskId}`}
          className={SELECT}
          value=""
          onChange={(e) =>
            e.target.value && onChange([...skills, { skill: e.target.value, level: 3, must: true }])
          }
        >
          <option value="">+ skill</option>
          {addable.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      ) : null}
    </div>
  )
}
