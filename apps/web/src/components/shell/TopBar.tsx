import { Search } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { CommandPalette } from './CommandPalette'
import { ProjectSwitcher } from './ProjectSwitcher'

export function TopBar() {
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setPaletteOpen((open) => !open)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const openPalette = useCallback(() => setPaletteOpen(true), [])

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-b bg-background px-4 md:px-6">
      <ProjectSwitcher />
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
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </header>
  )
}
