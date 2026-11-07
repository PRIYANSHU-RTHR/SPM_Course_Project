/** One definition of the S-curve series, shared by the chart and its legend. */
export const S_CURVE_SERIES = [
  { key: 'pv', name: 'Planned value', colour: 'var(--text-muted)', dash: '6 4' },
  { key: 'ev', name: 'Earned value', colour: 'var(--accent)', dash: undefined },
  { key: 'ac', name: 'Actual cost', colour: 'var(--warning)', dash: undefined },
] as const
