import { Search } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useCurrentProject } from '@/features/projects/useCurrentProject'
import { CommandPalette } from './CommandPalette'
import { ProjectSwitcher } from './ProjectSwitcher'
import { ShortcutsDialog } from './ShortcutsDialog'
import { goTarget, isShortcutEvent, SEQUENCE_MS } from './shortcuts'

export function TopBar() {
  const navigate = useNavigate()
  const { projectId } = useCurrentProject()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const gPressedAt = useRef(0)
  const projectRef = useRef(projectId)
  useEffect(() => {
    projectRef.current = projectId
  })

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setPaletteOpen((open) => !open)
        return
      }
      if (!isShortcutEvent(event)) return
      if (event.key === '?') {
        event.preventDefault()
        setShortcutsOpen(true)
        return
      }
      const now = event.timeStamp
      if (now - gPressedAt.current <= SEQUENCE_MS) {
        gPressedAt.current = 0
        const to = goTarget(event.key, projectRef.current)
        if (to) {
          event.preventDefault()
          navigate(to)
        }
        return
      }
      if (event.key === 'g') gPressedAt.current = now
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [navigate])

  const openPalette = useCallback(() => setPaletteOpen(true), [])

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-b bg-background px-4 md:px-6">
      <ProjectSwitcher />
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setShortcutsOpen(true)}
          aria-label="Keyboard shortcuts"
          className="hidden size-8 items-center justify-center rounded-lg border bg-surface font-mono text-xs text-muted-foreground outline-none transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring md:flex"
        >
          ?
        </button>
        <button
          type="button"
          onClick={openPalette}
          aria-label="Open command palette"
          className="flex h-8 shrink-0 items-center gap-2 rounded-lg border bg-surface px-2.5 text-muted-foreground outline-none transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Search className="size-4" strokeWidth={1.5} />
          <span className="hidden md:inline">Search pages</span>
          <kbd className="numeric hidden text-[11px] text-subtle md:inline">⌘K</kbd>
        </button>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <ShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </header>
  )
}
