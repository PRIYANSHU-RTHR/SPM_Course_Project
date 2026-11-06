import { createBrowserRouter, Navigate } from 'react-router'
import { AppShell } from '@/components/shell/AppShell'
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
      {
        path: 'projects',
        element: (
          <PlaceholderPage
            label="Projects"
            title="All projects"
            step={19}
            body="The projects table with deadline, progress, P(on time), SPI and open risks."
          />
        ),
      },
      {
        path: 'projects/:projectId',
        element: (
          <PlaceholderPage
            label="Overview"
            title="Project overview"
            step={19}
            body="KPI strip, S-curve, the next tasks on the critical path and the top risks."
          />
        ),
      },
      {
        path: 'projects/:projectId/schedule',
        element: (
          <PlaceholderPage
            label="Schedule"
            title="Schedule"
            step={21}
            body="Dependency network with the critical path, and the resource-levelled Gantt."
          />
        ),
      },
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
      {
        path: 'projects/:projectId/risks',
        element: (
          <PlaceholderPage
            label="Risks"
            title="Risk register"
            step={23}
            body="Probability × impact matrix, risk register and RMMM plans."
          />
        ),
      },
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
