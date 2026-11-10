import { Suspense } from 'react'
import { Outlet } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { LeftRail } from './LeftRail'
import { TopBar } from './TopBar'

/** Shown while a page's chunk loads: same rhythm as PageHeader + a panel. */
function PageSkeleton() {
  return (
    <div aria-busy="true">
      <Skeleton className="mb-1 h-4 w-20" />
      <Skeleton className="mb-6 h-8 w-72" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

export function AppShell() {
  return (
    <div className="flex min-h-svh">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="w-full max-w-[1280px] flex-1 px-4 py-6 md:px-6">
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
