import { formatDate, formatHours, formatPercent, formatRupees, formatTaskId } from '@/lib/format'
import { OWNER_COLOURS } from '@/lib/tokens'
import { Section } from './Section'

const COLOUR_TOKENS = [
  ['--bg', 'page'],
  ['--surface', 'cards, panels'],
  ['--surface-2', 'hover, inputs'],
  ['--border', 'hairlines'],
  ['--border-strong', 'focused, selected'],
  ['--text', 'body'],
  ['--text-muted', 'secondary'],
  ['--text-subtle', 'micro-labels'],
  ['--accent', 'brand, critical path'],
  ['--success', 'on track'],
  ['--warning', 'at risk'],
  ['--danger', 'off track'],
] as const

const FORMATS = [
  ['Hours', formatHours(18.5)],
  ['Percent', formatPercent(0.81)],
  ['Rupees', formatRupees('620000.00')],
  ['Date', formatDate('2026-12-18')],
  ['Task id', formatTaskId(14)],
] as const

export function TokenSections() {
  return (
    <>
      <Section title="Colour">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3 lg:grid-cols-6">
          {COLOUR_TOKENS.map(([name, use]) => (
            <div key={name} className="bg-surface p-3">
              <div
                className="h-10 rounded-lg border border-border-strong"
                style={{ background: `var(${name})` }}
              />
              <p className="numeric mt-2 truncate text-xs">{name}</p>
              <p className="truncate text-xs text-muted-foreground">{use}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Owner colours">
        <div className="flex flex-wrap gap-2">
          {OWNER_COLOURS.map((colour) => (
            <div key={colour} className="w-16">
              <div className="h-6 rounded-sm" style={{ background: colour }} />
              <p className="numeric mt-1 text-[11px] text-muted-foreground">{colour}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Type">
        <div className="flex flex-col gap-3 rounded-xl border bg-surface p-4">
          <p className="text-2xl leading-8 font-semibold tracking-tight">Page title, 24/600</p>
          <p className="text-[15px] leading-5 font-semibold">Section title, 15/600</p>
          <p>Body text, 14/400, used for tables, forms and descriptions.</p>
          <p className="text-muted-foreground">Secondary text in --text-muted.</p>
          <p className="micro-label">Micro-label, 11 mono uppercase</p>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-5">
            {FORMATS.map(([label, value]) => (
              <div key={label}>
                <dt className="micro-label">{label}</dt>
                <dd className="numeric">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Section>
    </>
  )
}
