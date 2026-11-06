import { useRouteError } from 'react-router'
import { Button } from '@/components/ui/button'

export function ErrorPage() {
  const error = useRouteError()
  const message = error instanceof Error ? error.message : 'Something went wrong.'

  return (
    <main className="mx-auto flex min-h-svh max-w-lg flex-col justify-center px-4">
      <p className="micro-label">Error</p>
      <h1 className="mt-1 text-2xl leading-8 font-semibold tracking-tight">This page failed</h1>
      <p className="numeric mt-2 text-muted-foreground">{message}</p>
      <div className="mt-4">
        <Button variant="outline" onClick={() => window.location.assign('/projects')}>
          Go to projects
        </Button>
      </div>
    </main>
  )
}
