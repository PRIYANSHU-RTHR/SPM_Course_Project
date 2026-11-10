import { KpiStat } from '@/components/KpiStat'
import type { PlanReview } from '@/lib/api/schemas'
import { formatDate, formatHours, formatRupees, formatShortDate } from '@/lib/format'

/** Engine numbers for the draft plan. Nothing here comes from the model. */
export function ReviewSummary({ review }: { review: PlanReview }) {
  const { estimates, schedule, recommendations } = review
  const overBudget = Number(estimates.estimated_cost) > Number(estimates.budget)
  const finish = recommendations.finish_with_owners ?? schedule.finish
  const late = finish > schedule.deadline

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <KpiStat
          label="Effort"
          value={formatHours(estimates.total_te_hours)}
          hint="Sum of PERT te = (o + 4m + p) / 6 over all tasks"
        />
        <KpiStat
          label="Cost"
          value={formatRupees(estimates.estimated_cost)}
          status={overBudget ? 'warning' : undefined}
          hint={`te × hourly rate. Budget ${formatRupees(estimates.budget)}`}
        />
        <KpiStat
          label="COCOMO II"
          value={estimates.cocomo ? `${estimates.cocomo.effort_pm.toFixed(1)} PM` : '—'}
          hint={
            estimates.cocomo
              ? `PM = A × KSLOC^E × ΠEM, E = ${estimates.cocomo.exponent.toFixed(2)}; ` +
                `${estimates.cocomo.ksloc.toFixed(1)} KSLOC; bottom-up is ` +
                `${estimates.total_effort_pm.toFixed(1)} PM`
              : 'Not available for this plan'
          }
        />
        <KpiStat
          label="Finish"
          value={formatShortDate(finish)}
          status={late ? 'danger' : undefined}
          hint={`${formatDate(finish)} with the recommended owners. Deadline ${formatDate(schedule.deadline)}`}
        />
        <KpiStat
          label="Unassigned"
          value={String(recommendations.unassigned)}
          status={recommendations.unassigned > 0 ? 'warning' : undefined}
          hint="Tasks nobody on the team is eligible for"
        />
      </div>
      {review.warnings.length > 0 ? (
        <ul className="flex flex-col gap-1 rounded-lg border border-warning/40 px-4 py-3">
          {review.warnings.map((warning) => (
            <li key={warning} className="text-warning">
              {warning}
            </li>
          ))}
        </ul>
      ) : null}
      {review.wbs.assumptions && review.wbs.assumptions.length > 0 ? (
        <details className="rounded-lg border px-4 py-3">
          <summary className="cursor-pointer text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring">
            {review.wbs.assumptions.length} assumptions in the draft
          </summary>
          <ul className="mt-2 list-disc pl-5 text-muted-foreground">
            {review.wbs.assumptions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  )
}
