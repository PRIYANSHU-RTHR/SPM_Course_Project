import {
  Activity,
  ChartGantt,
  ClipboardCheck,
  History,
  LayoutDashboard,
  ListTree,
  type LucideIcon,
  ShieldAlert,
  Users,
} from 'lucide-react'

export interface NavItem {
  label: string
  icon: LucideIcon
  to: string
  /** Pages that belong to a project fall back to the project list until one is known. */
  exact?: boolean
}

export function navItems(projectId: number | undefined): NavItem[] {
  const inProject = (suffix = '') =>
    projectId === undefined ? '/projects' : `/projects/${projectId}${suffix}`

  return [
    { label: 'Overview', icon: LayoutDashboard, to: inProject(), exact: true },
    { label: 'Plan', icon: ListTree, to: '/plan/new' },
    { label: 'Schedule', icon: ChartGantt, to: inProject('/schedule') },
    { label: 'Team', icon: Users, to: inProject('/team') },
    { label: 'Risks', icon: ShieldAlert, to: inProject('/risks') },
    { label: 'Control', icon: Activity, to: inProject('/control') },
    { label: 'Approvals', icon: ClipboardCheck, to: '/approvals' },
    { label: 'Audit', icon: History, to: '/audit' },
  ]
}
