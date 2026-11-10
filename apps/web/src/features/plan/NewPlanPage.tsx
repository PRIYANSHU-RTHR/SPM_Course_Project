import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { PlanExample } from '@/lib/api/schemas'
import { usePlanExample, useStartPlan } from './queries'

interface FormState {
  projectName: string
  brief: string
  startDate: string
  deadline: string
  budget: string
  hourlyRate: string
}

const EMPTY: FormState = {
  projectName: '',
  brief: '',
  startDate: '',
  deadline: '',
  budget: '',
  hourlyRate: '1250',
}

const MIN_BRIEF = 20

function fromExample(example: PlanExample): FormState {
  return {
    projectName: example.project_name,
    brief: example.brief,
    startDate: example.start_date ?? '',
    deadline: example.deadline,
    budget: String(Number(example.budget)),
    hourlyRate: String(Number(example.hourly_rate)),
  }
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="micro-label">
        {label}
      </label>
      {children}
    </div>
  )
}

export function NewPlanPage() {
  const navigate = useNavigate()
  const example = usePlanExample()
  const start = useStartPlan()
  const [form, setForm] = useState<FormState>(EMPTY)
  const set = (key: keyof FormState) => (value: string) => setForm((f) => ({ ...f, [key]: value }))

  const ready =
    form.projectName.trim() !== '' &&
    form.brief.trim().length >= MIN_BRIEF &&
    form.deadline !== '' &&
    form.budget !== '' &&
    Number(form.budget) >= 0

  const fillDemo = async () => {
    const result = await example.refetch()
    if (result.data) setForm(fromExample(result.data))
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!ready) return
    start.mutate(
      {
        project_name: form.projectName.trim(),
        brief: form.brief,
        deadline: form.deadline,
        start_date: form.startDate || null,
        budget: form.budget,
        hourly_rate: form.hourlyRate || '1250',
      },
      { onSuccess: ({ thread_id }) => navigate(`/plan/${thread_id}`) },
    )
  }

  return (
    <>
      <PageHeader label="New project" title="Plan from a brief">
        The planning workflow turns the brief into a WBS, estimates it, schedules it and
        recommends owners. You review the plan before anything is saved.
      </PageHeader>
      <form onSubmit={submit} className="flex max-w-3xl flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" size="sm" onClick={() => void fillDemo()}>
            {example.isFetching ? 'Loading' : 'Use the demo brief'}
          </Button>
          <span className="text-xs text-muted-foreground">
            Without a Gemini key the API replays recorded replies; the demo brief has one.
          </span>
        </div>
        {example.isError ? <p className="text-danger">{example.error.message}</p> : null}

        <Field id="plan-name" label="Project name">
          <Input
            id="plan-name"
            value={form.projectName}
            onChange={(e) => set('projectName')(e.target.value)}
            placeholder="Campus Food-Ordering App"
            maxLength={200}
          />
        </Field>
        <Field id="plan-brief" label="Brief">
          <Textarea
            id="plan-brief"
            value={form.brief}
            onChange={(e) => set('brief')(e.target.value)}
            rows={12}
            placeholder="What is being built, for whom, the main features and any constraints."
            className="font-mono text-[13px]"
          />
          <span className="numeric text-xs text-muted-foreground">
            {form.brief.length.toLocaleString('en-IN')} characters
            {form.brief.trim().length < MIN_BRIEF ? ` · at least ${MIN_BRIEF}` : ''}
          </span>
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field id="plan-start" label="Start (optional)">
            <Input
              id="plan-start"
              type="date"
              value={form.startDate}
              onChange={(e) => set('startDate')(e.target.value)}
            />
          </Field>
          <Field id="plan-deadline" label="Deadline">
            <Input
              id="plan-deadline"
              type="date"
              value={form.deadline}
              onChange={(e) => set('deadline')(e.target.value)}
            />
          </Field>
          <Field id="plan-budget" label="Budget (₹)">
            <Input
              id="plan-budget"
              type="number"
              min={0}
              step={1000}
              inputMode="numeric"
              className="numeric text-right"
              value={form.budget}
              onChange={(e) => set('budget')(e.target.value)}
            />
          </Field>
          <Field id="plan-rate" label="Hourly rate (₹)">
            <Input
              id="plan-rate"
              type="number"
              min={0}
              inputMode="numeric"
              className="numeric text-right"
              value={form.hourlyRate}
              onChange={(e) => set('hourlyRate')(e.target.value)}
            />
          </Field>
        </div>
        {start.isError ? <p className="text-danger">{start.error.message}</p> : null}
        <div>
          <Button type="submit" disabled={!ready || start.isPending}>
            {start.isPending ? 'Starting' : 'Generate plan'}
          </Button>
        </div>
      </form>
    </>
  )
}
