import type { ReactNode } from 'react'

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-[15px] leading-5 font-semibold">{title}</h2>
      {children}
    </section>
  )
}
