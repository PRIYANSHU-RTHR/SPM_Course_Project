import type { components } from './types'

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
