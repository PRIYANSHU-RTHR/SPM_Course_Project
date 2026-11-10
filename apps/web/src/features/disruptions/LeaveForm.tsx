import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { addDays } from '@/lib/dates'
import { Field, Footer } from './fields'
import { type FormProps, SELECT, useSubmit } from './useDisruptionForm'

export function LeaveForm(props: FormProps) {
  const { create, submit } = useSubmit(props)
  const [memberId, setMemberId] = useState('')
  const [start, setStart] = useState(addDays(props.today, 1))
  const [end, setEnd] = useState(addDays(props.today, 12))
  const [reason, setReason] = useState('')
  const valid = memberId !== '' && start !== '' && end >= start

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={submit({
        type: 'leave',
        member_id: Number(memberId),
        start_date: start,
        end_date: end,
        reason: reason.trim() || null,
      })}
    >
      <Field id="leave-member" label="Member">
        <select
          id="leave-member"
          className={SELECT}
          value={memberId}
          onChange={(e) => setMemberId(e.target.value)}
        >
          <option value="">Choose a member</option>
          {props.members.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} · {m.role}
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field id="leave-start" label="From">
          <Input
            id="leave-start"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </Field>
        <Field id="leave-end" label="To (inclusive)">
          <Input
            id="leave-end"
            type="date"
            value={end}
            min={start}
            onChange={(e) => setEnd(e.target.value)}
          />
        </Field>
      </div>
      <Field id="leave-reason" label="Reason (optional)">
        <Input
          id="leave-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Family emergency"
        />
      </Field>
      <Footer
        label="Record leave"
        disabled={!valid || props.blocked}
        pending={create.isPending}
        error={create.error?.message}
      />
    </form>
  )
}
