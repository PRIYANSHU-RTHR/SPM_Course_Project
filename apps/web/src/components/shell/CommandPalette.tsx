import { Palette } from 'lucide-react'
import { useNavigate } from 'react-router'
import { navItems } from '@/app/nav'
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { useCurrentProject } from '@/features/projects/useCurrentProject'

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate()
  const { projectId, projects } = useCurrentProject()

  function go(to: string) {
    onOpenChange(false)
    navigate(to)
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Command palette"
      description="Search for a page or project to open"
    >
      <Command>
        <CommandInput placeholder="Search pages and projects" />
        <CommandList>
          <CommandEmpty>No matching page.</CommandEmpty>
          <CommandGroup heading="Pages">
            {navItems(projectId).map(({ label, icon: Icon, to }) => (
              <CommandItem key={label} value={label} onSelect={() => go(to)}>
                <Icon className="size-4" strokeWidth={1.5} />
                {label}
              </CommandItem>
            ))}
            <CommandItem value="Styleguide" onSelect={() => go('/styleguide')}>
              <Palette className="size-4" strokeWidth={1.5} />
              Styleguide
            </CommandItem>
          </CommandGroup>
          {projects.length > 0 ? (
            <CommandGroup heading="Projects">
              {projects.map((item) => (
                <CommandItem
                  key={item.id}
                  value={item.name}
                  onSelect={() => go(`/projects/${item.id}`)}
                >
                  {item.name}
                </CommandItem>
              ))}
            </CommandGroup>
          ) : null}
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
