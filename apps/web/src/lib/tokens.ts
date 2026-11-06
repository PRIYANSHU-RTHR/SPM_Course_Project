/** Muted owner palette (55% saturation) for Gantt bars, heatmaps and initials chips. */
export const OWNER_COLOURS = [
  '#69A7D3',
  '#69D3B9',
  '#8CD369',
  '#D3BB69',
  '#D39069',
  '#D3697B',
  '#B969D3',
  '#6972D3',
] as const

/** Stable colour for a member id, so a person keeps one colour on every page. */
export function ownerColour(memberId: number): string {
  const index = Math.abs(memberId - 1) % OWNER_COLOURS.length
  return OWNER_COLOURS[index]
}
