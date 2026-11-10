import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { formatTaskId } from '@/lib/format'
import { Field, Footer } from './fields'
import { type FormProps, SELECT, useSubmit } from './useDisruptionForm'

export function SlipForm(props: FormProps) {
  const { create, submit } = useSubmit(props)
  const open = props.full.tasks.filter((t) => t.status !== 'done')
  const [taskId, setTaskId] = useState('')
  const [hours, setHours] = useState('16')
  const extra = Number(hours)
  const valid = taskId !== '' && extra > 0 && extra <= 200

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={submit({ type: 'slip', task_id: Number(taskId), extra_hours: extra })}
    >
      <Field id="slip-task" label="Task">
        <select
          id="slip-task"
          className={SELECT}
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
        >
          <option value="">Choose an open task</option>
          {open.map((t) => (
            <option key={t.id} value={t.id}>
              {formatTaskId(t.id)} {t.title}
            </option>
          ))}
        </select>
      </Field>
      <Field id="slip-hours" label="Extra hours (added to o, m and p)">
        <Input
          id="slip-hours"
          type="number"
          min={1}
          max={200}
          className="numeric text-right"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
        />
      </Field>
      <Footer
        label="Record slip"
        disabled={!valid || props.blocked}
        pending={create.isPending}
        error={create.error?.message}
      />
    </form>
  )
}

export function ScopeForm(props: FormProps) {
  const { create, submit } = useSubmit(props)
  const [title, setTitle] = useState('')
  const [epicId, setEpicId] = useState(String(props.full.epics[0]?.id ?? ''))
  const [omp, setOmp] = useState({ o: '8', m: '12', p: '20' })
  const [after, setAfter] = useState('')
  const [o, m, p] = [Number(omp.o), Number(omp.m), Number(omp.p)]
  const valid = title.trim() !== '' && epicId !== '' && 0 < o && o <= m && m <= p

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={submit({
        type: 'scope_add',
        task: {
          epic_id: Number(epicId),
          title: title.trim(),
          optimistic_hours: o,
          most_likely_hours: m,
          pessimistic_hours: p,
          priority: 2,
        },
        predecessors: after ? [Number(after)] : [],
      })}
    >
      <Field id="scope-title" label="Task">
        <Input
          id="scope-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="UPI refund flow"
          maxLength={200}
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field id="scope-epic" label="Epic">
          <select
            id="scope-epic"
            className={SELECT}
            value={epicId}
            onChange={(e) => setEpicId(e.target.value)}
          >
            {props.full.epics.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </select>
        </Field>
        <Field id="scope-after" label="After (optional)">
          <select
            id="scope-after"
            className={SELECT}
            value={after}
            onChange={(e) => setAfter(e.target.value)}
          >
            <option value="">No predecessor</option>
            {props.full.tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {formatTaskId(t.id)} {t.title}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {(['o', 'm', 'p'] as const).map((key) => (
          <Field key={key} id={`scope-${key}`} label={`${key} hours`}>
            <Input
              id={`scope-${key}`}
              type="number"
              min={1}
              className="numeric text-right"
              value={omp[key]}
              onChange={(e) => setOmp((v) => ({ ...v, [key]: e.target.value }))}
            />
          </Field>
        ))}
      </div>
      <Footer
        label="Add scope"
        disabled={!valid || props.blocked}
        pending={create.isPending}
        error={create.error?.message}
      />
    </form>
  )
}
