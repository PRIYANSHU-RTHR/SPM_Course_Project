import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useGenerateRiskPlan } from '@/features/projects/queries'
import { ApiError } from '@/lib/api/client'
import type { Risk } from '@/lib/api/schemas'
import { formatRiskId } from '@/lib/format'
import { RiskStatusBadge } from './RiskRegister'
import { evidenceLabel, evidenceValue, parseRmmm, type RmmmPlan } from './riskMetrics'

function PlanSection({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h4 className="micro-label">{title}</h4>
      <p className="mt-0.5">{text || '—'}</p>
    </div>
  )
}

function PlanSource({ plan }: { plan: RmmmPlan }) {
  if (plan.source === 'template') return <Badge variant="outline">template</Badge>
  if (plan.grounded) return <Badge variant="outline">grounded</Badge>
  return null
}

function generateError(error: Error): string {
  if (error instanceof ApiError && error.status === 404 && error.code === 'unknown_error') {
    return 'Plan generation is not available on this API yet.'
  }
  return error.message
}

interface RiskSheetProps {
  projectId: number
  risk: Risk | undefined
  onClose: () => void
}

export function RiskSheet({ projectId, risk, onClose }: RiskSheetProps) {
  const generate = useGenerateRiskPlan(projectId)
  const plan = risk ? parseRmmm(risk.rmmm) : null
  const evidence = risk ? Object.entries(risk.evidence) : []

  return (
    <Sheet
      open={risk !== undefined}
      onOpenChange={(open) => {
        if (!open) {
          generate.reset()
          onClose()
        }
      }}
    >
      <SheetContent className="overflow-y-auto">
        {risk ? (
          <>
            <SheetHeader>
              <p className="numeric text-xs text-muted-foreground">{formatRiskId(risk.id)}</p>
              <SheetTitle>{risk.title}</SheetTitle>
              <SheetDescription className="sr-only">
                Evidence and response plan for this risk.
              </SheetDescription>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <RiskStatusBadge status={risk.status} />
                <span className="numeric text-muted-foreground">
                  P{risk.probability} × I{risk.impact} = {risk.score}
                </span>
                <span className="text-muted-foreground capitalize">{risk.category}</span>
              </div>
            </SheetHeader>
            <div className="flex flex-col gap-5 px-4 pb-6">
              <section>
                <h3 className="text-[15px] leading-5 font-semibold">Evidence</h3>
                {evidence.length === 0 ? (
                  <p className="mt-1 text-muted-foreground">No numbers were recorded.</p>
                ) : (
                  <dl className="mt-2 grid grid-cols-2 gap-3">
                    {evidence.map(([key, value]) => (
                      <div key={key}>
                        <dt className="micro-label">{evidenceLabel(key)}</dt>
                        <dd className="numeric mt-0.5">{evidenceValue(value)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </section>
              <section className="flex flex-col gap-3">
                <h3 className="text-[15px] leading-5 font-semibold">RMMM plan</h3>
                {plan ? (
                  <>
                    <div className="flex items-center gap-2">
                      <p className="micro-label">Gemini · RMMM plan</p>
                      <PlanSource plan={plan} />
                    </div>
                    <PlanSection title="Mitigation" text={plan.mitigation} />
                    <PlanSection title="Monitoring trigger" text={plan.monitoringTrigger} />
                    <PlanSection title="Contingency" text={plan.contingency} />
                    <PlanSection title="Owner role" text={plan.ownerRole} />
                  </>
                ) : (
                  <div className="flex flex-col items-start gap-3">
                    <p className="text-muted-foreground">This risk has no plan yet.</p>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={generate.isPending}
                      onClick={() => generate.mutate(risk.id)}
                    >
                      {generate.isPending ? 'Generating plan' : 'Generate plan'}
                    </Button>
                    {generate.isError ? (
                      <p className="text-danger">{generateError(generate.error)}</p>
                    ) : null}
                  </div>
                )}
              </section>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
