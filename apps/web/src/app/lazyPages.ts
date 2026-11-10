import { lazy } from 'react'

// One chunk per page: the shell renders at once, each page (and its chart libraries) loads
// on first visit. AppShell wraps the outlet in Suspense.
export const ControlPage = lazy(() =>
  import('@/features/control/ControlPage').then((m) => ({ default: m.ControlPage })),
)
export const ApprovalsPage = lazy(() =>
  import('@/features/disruptions/ApprovalsPage').then((m) => ({ default: m.ApprovalsPage })),
)
export const AuditPage = lazy(() =>
  import('@/features/disruptions/AuditPage').then((m) => ({ default: m.AuditPage })),
)
export const NewPlanPage = lazy(() =>
  import('@/features/plan/NewPlanPage').then((m) => ({ default: m.NewPlanPage })),
)
export const PlanRunPage = lazy(() =>
  import('@/features/plan/PlanRunPage').then((m) => ({ default: m.PlanRunPage })),
)
export const OverviewPage = lazy(() =>
  import('@/features/projects/OverviewPage').then((m) => ({ default: m.OverviewPage })),
)
export const ProjectsPage = lazy(() =>
  import('@/features/projects/ProjectsPage').then((m) => ({ default: m.ProjectsPage })),
)
export const RisksPage = lazy(() =>
  import('@/features/risks/RisksPage').then((m) => ({ default: m.RisksPage })),
)
export const SchedulePage = lazy(() =>
  import('@/features/schedule/SchedulePage').then((m) => ({ default: m.SchedulePage })),
)
export const StyleguidePage = lazy(() =>
  import('@/features/styleguide/StyleguidePage').then((m) => ({ default: m.StyleguidePage })),
)
export const TeamPage = lazy(() =>
  import('@/features/team/TeamPage').then((m) => ({ default: m.TeamPage })),
)
