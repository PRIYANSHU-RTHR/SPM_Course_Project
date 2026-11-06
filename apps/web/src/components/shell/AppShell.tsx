import { Outlet } from 'react-router'
import { LeftRail } from './LeftRail'
import { TopBar } from './TopBar'

export function AppShell() {
  return (
    <div className="flex min-h-svh">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="w-full max-w-[1280px] flex-1 px-4 py-6 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
