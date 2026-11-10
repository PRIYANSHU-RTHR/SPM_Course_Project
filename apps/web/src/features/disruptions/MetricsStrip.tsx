import { AnimatedNumber } from '@/components/AnimatedNumber'
import { KpiStat, KpiStatSkeleton } from '@/components/KpiStat'
import { formatDate, formatPercent, formatRatio } from '@/lib/format'
import { useMetrics } from './queries'

const percent = (v: number) => formatPercent(v)
const ratio = (v: number) => formatRatio(v)
const whole = (v: number) => String(Math.round(v))
const dash = <span className="text-subtle">—</span>

/** One call to /metrics; values ease from before to after when it refetches (e.g. on approval). */
export function MetricsStrip({ projectId }: { projectId: number }) {
  const metrics = useMetrics(projectId)
  const m = metrics.data

  if (metrics.isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <KpiStatSkeleton key={i} />
        ))}
      </div>
    )
  }
  if (!m) return <p className="text-danger">{metrics.error?.message ?? 'Metrics unavailable.'}</p>

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <KpiStat
        label="P(on time)"
        status={m.p_on_time !== null && m.p_on_time < 0.6 ? 'danger' : undefined}
        hint="Resource-adjusted Monte Carlo: share of runs finishing by the deadline"
        value={
          m.p_on_time !== null ? <AnimatedNumber value={m.p_on_time} format={percent} /> : dash
        }
      />
      <KpiStat
        label="P80 finish"
        status={m.p80 !== null && m.p80 > m.deadline ? 'warning' : undefined}
        hint={`80% of runs finish by this date. Deadline ${formatDate(m.deadline)}`}
        value={formatDate(m.p80)}
      />
      <KpiStat
        label="SPI"
        status={m.spi !== null && m.spi < 0.9 ? 'danger' : undefined}
        hint="SPI = EV / PV"
        value={m.spi !== null ? <AnimatedNumber value={m.spi} format={ratio} /> : dash}
      />
      <KpiStat
        label="CPI"
        status={m.cpi !== null && m.cpi < 0.9 ? 'danger' : undefined}
        hint="CPI = EV / AC"
        value={m.cpi !== null ? <AnimatedNumber value={m.cpi} format={ratio} /> : dash}
      />
      <KpiStat
        label="Open risks"
        hint="Risks the rules raise at the project clock"
        value={<AnimatedNumber value={m.open_risks} format={whole} />}
      />
      <KpiStat
        label="Overloaded"
        status={m.overloaded_members > 0 ? 'warning' : undefined}
        hint="Members above 100% of capacity in at least one week"
        value={<AnimatedNumber value={m.overloaded_members} format={whole} />}
      />
    </div>
  )
}
