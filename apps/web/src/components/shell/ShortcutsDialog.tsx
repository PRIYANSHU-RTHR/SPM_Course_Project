import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { GO_SHORTCUTS } from './shortcuts'

function Keys({ keys }: { keys: string[] }) {
  return (
    <span className="flex gap-1">
      {keys.map((key) => (
        <kbd
          key={key}
          className="min-w-6 rounded-md border bg-surface-2 px-1.5 text-center font-mono text-xs leading-5"
        >
          {key}
        </kbd>
      ))}
    </span>
  )
}

const GENERAL: { keys: string[]; label: string }[] = [
  { keys: ['⌘', 'K'], label: 'Command palette (Ctrl K on Windows and Linux)' },
  { keys: ['?'], label: 'This list' },
]

export function ShortcutsDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>Press g, then a letter, to jump to a page.</DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-2">
          {GENERAL.map(({ keys, label }) => (
            <div key={label} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd>
                <Keys keys={keys} />
              </dd>
            </div>
          ))}
          {GO_SHORTCUTS.map(({ key, label }) => (
            <div key={key} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd>
                <Keys keys={['g', key]} />
              </dd>
            </div>
          ))}
        </dl>
      </DialogContent>
    </Dialog>
  )
}
