import { Plus } from 'lucide-react'
import { KpiStat } from '@/components/KpiStat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Section } from './Section'

/** Sample values for display only. Real KPIs come from the engines. */
export function ComponentSections() {
  return (
    <>
      <Section title="Buttons and inputs">
        <div className="flex flex-wrap items-center gap-2">
          <Button>Approve plan</Button>
          <Button variant="secondary">Send edits</Button>
          <Button variant="outline">Override</Button>
          <Button variant="ghost">Cancel</Button>
          <Button variant="destructive">Reject</Button>
          <Button variant="outline" size="icon" aria-label="Add task">
            <Plus strokeWidth={1.5} />
          </Button>
          <Button disabled>Disabled</Button>
          <Input className="w-56" placeholder="Search tasks" aria-label="Search tasks" />
        </div>
      </Section>

      <Section title="Badges">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">Todo</Badge>
          <Badge variant="secondary">In progress</Badge>
          <Badge variant="success">Done</Badge>
          <Badge variant="warning">Blocked</Badge>
          <Badge variant="danger">Over capacity</Badge>
          <Badge>PM override</Badge>
        </div>
      </Section>

      <Section title="KPI stat">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiStat
            label="P(on time)"
            value="81%"
            delta="+4 pts"
            tone="success"
            hint="Share of 5,000 runs finishing by the deadline"
          />
          <KpiStat label="SPI" value="0.92" delta="−0.03" tone="warning" hint="SPI = EV / PV" />
          <KpiStat label="CPI" value="1.04" delta="+0.01" tone="success" hint="CPI = EV / AC" />
          <KpiStat label="Open risks" value="7" delta="+2" tone="danger" />
        </div>
      </Section>

      <Section title="Loading">
        <div className="flex max-w-md flex-col gap-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      </Section>
    </>
  )
}
