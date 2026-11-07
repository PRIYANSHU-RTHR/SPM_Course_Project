import { Link } from 'react-router'
import { PageHeader } from '@/components/PageHeader'
import { Panel, PanelEmpty, PanelError } from '@/components/Panel'
import { buttonVariants } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ProjectRow } from './ProjectRow'
import { useProjects } from './queries'

const NEW_PROJECT = buttonVariants({ variant: 'default', size: 'default' })

export function ProjectsPage() {
  const { data, isLoading, isError, error, refetch } = useProjects()

  return (
    <>
      <PageHeader label="Projects" title="All projects" />
      <Panel title="Portfolio" action={{ label: 'New project', to: '/plan/new' }}>
        {isLoading ? (
          <div className="flex flex-col gap-2 p-3">
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} className="h-7 w-full" />
            ))}
          </div>
        ) : isError ? (
          <PanelError message={error.message} onRetry={() => void refetch()} />
        ) : !data || data.items.length === 0 ? (
          <PanelEmpty
            action={
              <Link to="/plan/new" className={NEW_PROJECT}>
                Plan a project
              </Link>
            }
          >
            No projects yet.
          </PanelEmpty>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">ID</TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Deadline</TableHead>
                <TableHead className="w-44">Progress</TableHead>
                <TableHead className="text-right">P(on time)</TableHead>
                <TableHead className="text-right">SPI</TableHead>
                <TableHead className="text-right">Open risks</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((project) => (
                <ProjectRow key={project.id} project={project} />
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>
    </>
  )
}
