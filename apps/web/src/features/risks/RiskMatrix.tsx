import { cn } from '@/lib/utils'
import { type Cell, cellKey, cellTint } from './riskMetrics'

const LEVELS = [1, 2, 3, 4, 5]

interface RiskMatrixProps {
  counts: Map<string, number>
  selected: Cell | null
  onSelect: (cell: Cell | null) => void
}

export function RiskMatrix({ counts, selected, onSelect }: RiskMatrixProps) {
  return (
    <div className="flex gap-2 p-4">
      <p className="micro-label self-center [writing-mode:vertical-rl] rotate-180">Probability</p>
      <div className="min-w-0 flex-1">
        <div className="grid grid-cols-[20px_repeat(5,minmax(0,1fr))] gap-1">
          {[...LEVELS].reverse().map((probability) => (
            <div key={probability} className="contents">
              <span className="numeric flex items-center justify-center text-[11px] text-subtle">
                {probability}
              </span>
              {LEVELS.map((impact) => {
                const cell = { probability, impact }
                const score = probability * impact
                const count = counts.get(cellKey(cell)) ?? 0
                const isSelected =
                  selected?.probability === probability && selected.impact === impact
                return (
                  <button
                    key={impact}
                    type="button"
                    disabled={count === 0}
                    aria-pressed={isSelected}
                    aria-label={`Probability ${probability}, impact ${impact}, score ${score}, ${count} ${count === 1 ? 'risk' : 'risks'}`}
                    onClick={() => onSelect(isSelected ? null : cell)}
                    className={cn(
                      'numeric flex aspect-square max-h-14 w-full items-center justify-center rounded-sm text-sm outline-none transition-colors duration-150 ease-out enabled:cursor-pointer enabled:hover:ring-1 enabled:hover:ring-border-strong focus-visible:ring-2 focus-visible:ring-ring disabled:text-transparent',
                      isSelected && 'ring-2 ring-brand',
                    )}
                    style={{
                      background: `color-mix(in srgb, var(--danger) ${cellTint(score)}%, var(--surface))`,
                    }}
                  >
                    {count}
                  </button>
                )
              })}
            </div>
          ))}
          <span />
          {LEVELS.map((impact) => (
            <span key={impact} className="numeric text-center text-[11px] text-subtle">
              {impact}
            </span>
          ))}
        </div>
        <p className="micro-label mt-1 pl-5 text-center">Impact</p>
      </div>
    </div>
  )
}
