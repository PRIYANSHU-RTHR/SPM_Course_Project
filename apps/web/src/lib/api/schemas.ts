import type { components, paths } from './types'

type Schemas = components['schemas']

export type Project = Schemas['ProjectRead']
export type ProjectPage = Schemas['ProjectPage']
export type ProjectFull = Schemas['ProjectFull']
export type Epic = Schemas['EpicRead']
export type Task = Schemas['TaskRead']
export type TaskStatus = Task['status']
export type MemberPage = Schemas['MemberPage']
export type Member = Schemas['MemberRead']
export type ProjectForecast = Schemas['ProjectForecast']
export type ProjectEvm = Schemas['ProjectEvm']
export type ProjectCpm = Schemas['ProjectCpm']
export type ProjectSchedule = Schemas['ProjectSchedule']
export type WeekLoad = Schemas['WeekLoadOut']
export type Risk = Schemas['RiskRead']
export type RiskPage = Schemas['RiskPage']
export type RiskRefreshResult = Schemas['RiskRefreshResult']
export type RecommendResponse = Schemas['RecommendResponse']
export type Recommendation = Schemas['RecommendationOut']
export type Candidate = Schemas['CandidateOut']
export type Score = Schemas['ScoreOut']
export type Assignment = Schemas['AssignmentRead']
export type ApplyRequest = Schemas['ApplyRequest']
export type AppliedAssignment = Schemas['AppliedAssignment']
export type ScheduledTask = Schemas['ScheduledTaskOut']

/** Hand-written until Step 16 merges, then replace with the generated `Explanation` type. */
export interface Explanation {
  recommended_member_id: number | null
  text: string
  grounded: boolean
  source: 'model' | 'template'
}

// Planning workflow (Step 20)
/** Request body for `POST /workflows/plan`. */
export type PlanStart = Schemas['PlanStart-Input']
/** `GET /workflows/plan/example`: the demo brief with defaults. */
export type PlanExample = Schemas['PlanStart-Output']
export type PlanStarted = Schemas['PlanStarted']
export type PlanReview = Schemas['PlanReview']
export type PlannedTask = Schemas['PlannedTask']
export type SkillReq = Schemas['SkillReq']
export type TaskChange = Schemas['TaskChange']
export type ApproveDecision = Schemas['ApproveDecision']
export type EditDecision = Schemas['EditDecision']
export type RejectDecision = Schemas['RejectDecision']
export type ResumeAccepted = Schemas['ResumeAccepted']
export type WorkflowState = Schemas['WorkflowState']
/** One SSE message from `/workflows/{thread_id}/events` (inlined in the OpenAPI response). */
export type WorkflowEvent =
  paths['/workflows/{thread_id}/events']['get']['responses'][200]['content']['text/event-stream']
export type WorkflowStatus = WorkflowState['status']
export type SkillPage = Schemas['SkillPage']
