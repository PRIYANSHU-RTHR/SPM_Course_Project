import { Link } from 'react-router'
import { PageHeader } from '@/components/PageHeader'

interface PlaceholderPageProps {
  label: string
  title: string
  step: number
  body: string
}

export function PlaceholderPage({ label, title, step, body }: PlaceholderPageProps) {
  return (
    <>
      <PageHeader label={label} title={title} />
      <section className="rounded-xl border bg-surface p-6">
        <p className="micro-label">Step {String(step).padStart(2, '0')}</p>
        <p className="mt-2 max-w-prose text-muted-foreground">{body}</p>
        <Link
          to="/styleguide"
          className="mt-4 inline-block rounded-sm text-brand underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          Open the styleguide
        </Link>
      </section>
    </>
  )
}
