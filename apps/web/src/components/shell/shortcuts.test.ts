import { describe, expect, it } from 'vitest'
import { goTarget, isShortcutEvent } from './shortcuts'

const event = (
  target: unknown,
  mods: Partial<Record<'metaKey' | 'ctrlKey' | 'altKey', boolean>> = {},
) => ({
  metaKey: false,
  ctrlKey: false,
  altKey: false,
  ...mods,
  target: target as EventTarget,
})

describe('shortcuts', () => {
  it('maps g + key to pages, using the current project where needed', () => {
    expect(goTarget('p', 3)).toBe('/projects')
    expect(goTarget('s', 3)).toBe('/projects/3/schedule')
    expect(goTarget('S', 3)).toBe('/projects/3/schedule')
    expect(goTarget('s', undefined)).toBe('/projects')
    expect(goTarget('a', undefined)).toBe('/approvals')
    expect(goTarget('x', 3)).toBeUndefined()
  })

  it('ignores typing in fields and modifier chords', () => {
    const field = { closest: (sel: string) => (sel.includes('input') ? {} : null) }
    const body = { closest: () => null }
    expect(isShortcutEvent(event(body))).toBe(true)
    expect(isShortcutEvent(event(field))).toBe(false)
    expect(isShortcutEvent(event(body, { metaKey: true }))).toBe(false)
    expect(isShortcutEvent(event(null))).toBe(true)
  })
})
