import { Link } from 'react-router'
import { PageHeader } from '@/components/PageHeader'

export function NotFoundPage() {
  return (
    <>
      <PageHeader label="404" title="Page not found" />
      <p className="text-muted-foreground">This address does not match any page.</p>
      <Link
        to="/projects"
        className="mt-4 inline-block rounded-sm text-brand underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
      >
        Go to projects
      </Link>
    </>
  )
}
