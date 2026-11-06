import type { ReactNode } from 'react'

interface PageHeaderProps {
  label: string
  title: string
  children?: ReactNode
}

export function PageHeader({ label, title, children }: PageHeaderProps) {
  return (
    <header className="mb-6">
      <p className="micro-label">{label}</p>
      <h1 className="mt-1 text-2xl leading-8 font-semibold tracking-tight">{title}</h1>
      {children ? <div className="mt-1 text-muted-foreground">{children}</div> : null}
    </header>
  )
}
