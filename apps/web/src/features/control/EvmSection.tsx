import { KpiStat, KpiStatSkeleton } from '@/components/KpiStat'
import { PanelError } from '@/components/Panel'
import { indexStatus } from '@/features/projects/metrics'
import { useEvm } from '@/features/projects/queries'
import { SCurvePanel } from '@/features/projects/SCurvePanel'
import type { ProjectEvm } from '@/lib/api/schemas'
import { formatRatio, formatRupees } from '@/lib/format'

type Status = 'warning' | 'danger' | undefined

interface Metric {
  label: string
  value: string
  formula: string
  status: Status
}

const negative = (value: string | null | undefined): Status =>
  value != null && Number(value) < 0 ? 'warning' : undefined

function metrics(evm: ProjectEvm): Metric[] {
  const why = (key: string, formula: string) =>
    evm.notes[key] ? `${formula}. ${evm.notes[key]}` : formula
  return [
    { label: 'SV', value: formatRupees(evm.sv), formula: 'SV = EV − PV', status: negative(evm.sv) },
    { label: 'CV', value: formatRupees(evm.cv), formula: 'CV = EV − AC', status: negative(evm.cv) },
    {
      label: 'SPI',
      value: formatRatio(evm.spi),
      formula: why('spi', 'SPI = EV / PV'),
      status: indexStatus(evm.spi),
    },
    {
      label: 'CPI',
      value: formatRatio(evm.cpi),
      formula: why('cpi', 'CPI = EV / AC'),
      status: indexStatus(evm.cpi),
    },
    {
      label: 'EAC',
      value: formatRupees(evm.eac),
      formula: why('eac', 'EAC = BAC / CPI'),
      status: negative(evm.vac),
    },
    {
      label: 'ETC',
      value: formatRupees(evm.etc),
      formula: why('etc', 'ETC = EAC − AC'),
      status: undefined,
    },
    {
      label: 'VAC',
      value: formatRupees(evm.vac),
      formula: why('vac', 'VAC = BAC − EAC'),
      status: negative(evm.vac),
    },
    {
      label: 'TCPI',
      value: formatRatio(evm.tcpi),
      formula: why('tcpi', 'TCPI = (BAC − EV) / (BAC − AC)'),
      status: evm.tcpi != null && evm.tcpi > 1 ? 'warning' : undefined,
    },
  ]
}

export function EvmSection({ projectId }: { projectId: number }) {
  const evm = useEvm(projectId)

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-[15px] leading-5 font-semibold">Earned value</h2>
      {evm.isError ? (
        <div className="rounded-xl border bg-surface">
          <PanelError message={evm.error.message} onRetry={() => void evm.refetch()} />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {evm.data
            ? metrics(evm.data).map(({ label, value, formula, status }) => (
                <KpiStat
                  key={label}
                  label={label}
                  value={<span className="text-xl leading-8">{value}</span>}
                  hint={formula}
                  status={status}
                />
              ))
            : Array.from({ length: 8 }, (_, index) => <KpiStatSkeleton key={index} />)}
        </div>
      )}
      <SCurvePanel projectId={projectId} />
    </section>
  )
}
