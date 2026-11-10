/** Keyboard shortcuts: `?` opens the sheet, `g` then a letter goes to a page. Pure helpers. */

export interface GoShortcut {
  key: string
  label: string
  /** Pages inside a project fall back to the project list until one is known. */
  to: (projectId: number | undefined) => string
}

const inProject = (suffix: string) => (id: number | undefined) =>
  id === undefined ? '/projects' : `/projects/${id}${suffix}`

export const GO_SHORTCUTS: GoShortcut[] = [
  { key: 'p', label: 'Projects', to: () => '/projects' },
  { key: 'o', label: 'Overview', to: inProject('') },
  { key: 'n', label: 'New plan', to: () => '/plan/new' },
  { key: 's', label: 'Schedule', to: inProject('/schedule') },
  { key: 't', label: 'Team', to: inProject('/team') },
  { key: 'r', label: 'Risks', to: inProject('/risks') },
  { key: 'c', label: 'Control', to: inProject('/control') },
  { key: 'a', label: 'Approvals', to: () => '/approvals' },
  { key: 'l', label: 'Audit log', to: () => '/audit' },
]

/** How long `g` waits for its second key. */
export const SEQUENCE_MS = 1000

/** The route for `g` + key, if it is a shortcut. */
export function goTarget(key: string, projectId: number | undefined): string | undefined {
  return GO_SHORTCUTS.find((s) => s.key === key.toLowerCase())?.to(projectId)
}

/** Typing in a field, or a chord with a modifier, is never a shortcut. */
export function isShortcutEvent(
  event: Pick<KeyboardEvent, 'metaKey' | 'ctrlKey' | 'altKey' | 'target'>,
): boolean {
  if (event.metaKey || event.ctrlKey || event.altKey) return false
  const target = event.target as HTMLElement | null
  if (!target || typeof target.closest !== 'function') return true
  return (
    target.closest('input, textarea, select, [contenteditable="true"], [role="dialog"]') === null
  )
}
