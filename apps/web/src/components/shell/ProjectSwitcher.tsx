import { Check, ChevronsUpDown } from 'lucide-react'
import { useNavigate } from 'react-router'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { useCurrentProject } from '@/features/projects/useCurrentProject'

export function ProjectSwitcher() {
  const { project, projects, isLoading, isError } = useCurrentProject()
  const navigate = useNavigate()

  if (isLoading) return <Skeleton className="h-8 w-52" />
  if (isError) return <p className="truncate text-danger">Could not load projects</p>
  if (projects.length === 0) return <p className="text-muted-foreground">No projects yet</p>

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Switch project, current project ${project?.name ?? 'not selected'}`}
        className="flex h-8 min-w-0 items-center gap-2 rounded-lg px-2 font-medium outline-none transition-colors duration-150 ease-out hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring">
        <span className="truncate">{project?.name ?? 'Select a project'}</span>
        <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuLabel className="micro-label">Projects</DropdownMenuLabel>
        {projects.map((item) => (
          <DropdownMenuItem key={item.id} onSelect={() => navigate(`/projects/${item.id}`)}>
            <span className="min-w-0 flex-1 truncate">{item.name}</span>
            {item.id === project?.id ? (
              <Check className="size-4 text-brand" strokeWidth={1.5} />
            ) : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
