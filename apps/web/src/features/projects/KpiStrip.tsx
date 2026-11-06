import { AnimatedNumber } from '@/components/AnimatedNumber'
import { KpiStat, KpiStatSkeleton } from '@/components/KpiStat'
import { formatDelta, formatPercent, formatRatio } from '@/lib/format'
import { evmDeltas, forecastStatus, indexStatus, openRisks, overloadedMembers } from './metrics'
import { useCpm, useEvm, useForecast, useRisks, useSchedule } from './queries'

const whole = (value: number) => String(Math.round(value))
const percent = (value: number) => formatPercent(value)
const ratio = (value: number) => formatRatio(value)

const unavailable = <span className="text-subtle">—</span>

export function KpiStrip({ projectId }: { projectId: number }) {
  const forecast = useForecast(projectId)
  const evm = useEvm(projectId)
  const cpm = useCpm(projectId)
  const schedule = useSchedule(projectId)
  const risks = useRisks(projectId)
  const deltas = evm.data ? evmDeltas(evm.data) : null
  const overloaded = schedule.data ? overloadedMembers(schedule.data.loads) : null

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {forecast.isLoading ? (
        <KpiStatSkeleton />
      ) : (
        <KpiStat
          label="P(on time)"
          status={forecast.data ? forecastStatus(forecast.data.p_on_time) : undefined}
          hint="Share of Monte Carlo runs finishing by the deadline"
          value={
            forecast.data ? (
              <AnimatedNumber value={forecast.data.p_on_time} format={percent} />
            ) : (
              unavailable
            )
          }
        />
      )}
      {evm.isLoading ? (
        <KpiStatSkeleton />
      ) : (
        <KpiStat
          label="SPI"
          status={indexStatus(evm.data?.spi)}
          delta={formatDelta(deltas?.spi)}
          hint="SPI = EV / PV. Change is against the previous snapshot."
          value={evm.data?.spi != null ? <AnimatedNumber value={evm.data.spi} format={ratio} /> : unavailable}
        />
      )}
      {evm.isLoading ? (
        <KpiStatSkeleton />
      ) : (
        <KpiStat
          label="CPI"
          status={indexStatus(evm.data?.cpi)}
          delta={formatDelta(deltas?.cpi)}
          hint="CPI = EV / AC. Change is against the previous snapshot."
          value={evm.data?.cpi != null ? <AnimatedNumber value={evm.data.cpi} format={ratio} /> : unavailable}
        />
      )}
      {cpm.isLoading ? (
        <KpiStatSkeleton />
      ) : (
        <KpiStat
          label="Critical tasks"
          hint="Tasks with zero total slack: LS − ES = 0"
          value={
            cpm.data ? (
              <AnimatedNumber
                value={cpm.data.tasks.filter((task) => task.critical).length}
                format={whole}
              />
            ) : (
              unavailable
            )
          }
        />
      )}
      {schedule.isLoading ? (
        <KpiStatSkeleton />
      ) : (
        <KpiStat
          label="Overloaded"
          status={overloaded ? 'warning' : undefined}
          hint="Members above 100% utilisation in any ISO week"
          value={overloaded !== null ? <AnimatedNumber value={overloaded} format={whole} /> : unavailable}
        />
      )}
      {risks.isLoading ? (
        <KpiStatSkeleton />
      ) : (
        <KpiStat
          label="Open risks"
          hint="Risks in the register that are not closed"
          value={
            risks.data ? (
              <AnimatedNumber value={openRisks(risks.data.items).length} format={whole} />
            ) : (
              unavailable
            )
          }
        />
      )}
    </div>
  )
}
