import { createBrowserRouter, Navigate } from 'react-router'
import { AppShell } from '@/components/shell/AppShell'
import { ControlPage } from '@/features/control/ControlPage'
import { OverviewPage } from '@/features/projects/OverviewPage'
import { ProjectsPage } from '@/features/projects/ProjectsPage'
import { RisksPage } from '@/features/risks/RisksPage'
import { SchedulePage } from '@/features/schedule/SchedulePage'
import { StyleguidePage } from '@/features/styleguide/StyleguidePage'
import { ErrorPage } from './pages/ErrorPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PlaceholderPage } from './pages/PlaceholderPage'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: 'projects', element: <ProjectsPage /> },
      { path: 'projects/:projectId', element: <OverviewPage /> },
      { path: 'projects/:projectId/schedule', element: <SchedulePage /> },
      {
        path: 'projects/:projectId/team',
        element: (
          <PlaceholderPage
            label="Team"
            title="Team and assignments"
            step={22}
            body="Skills matrix, capacity heatmap and explainable assignment review."
          />
        ),
      },
      { path: 'projects/:projectId/risks', element: <RisksPage /> },
      { path: 'projects/:projectId/control', element: <ControlPage /> },
      {
        path: 'plan/new',
        element: (
          <PlaceholderPage
            label="Plan"
            title="New project plan"
            step={20}
            body="Brief to plan, with the live workflow timeline and WBS review."
          />
        ),
      },
      {
        path: 'approvals',
        element: (
          <PlaceholderPage
            label="Approvals"
            title="Approvals"
            step={24}
            body="Pending reallocation proposals with before and after metrics."
          />
        ),
      },
      {
        path: 'audit',
        element: (
          <PlaceholderPage
            label="Audit"
            title="Audit log"
            step={24}
            body="Who approved or changed what, when and why."
          />
        ),
      },
      { path: 'styleguide', element: <StyleguidePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
