import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'

export function Field({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="micro-label">
        {label}
      </label>
      {children}
    </div>
  )
}

export function Footer({
  label,
  disabled,
  pending,
  error,
}: {
  label: string
  disabled: boolean
  pending: boolean
  error?: string
}) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <Button type="submit" disabled={disabled || pending}>
          {pending ? 'Starting' : label}
        </Button>
      </div>
      {error ? <p className="text-danger">{error}</p> : null}
    </div>
  )
}
