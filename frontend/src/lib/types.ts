export type Role = "ADMIN" | "EMPLOYEE"

export const ROLES: Role[] = ["ADMIN", "EMPLOYEE"]

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Administrateur",
  EMPLOYEE: "Employé",
}

export interface User {
  id: string
  email: string
  name: string
  role: Role
  teams: string[]
}

export interface MemberRef {
  id: string
  name: string
  email: string
}

export interface DocumentRef {
  id: string
  title: string
}

export interface Doc {
  id: string
  title: string
  department: string
  status: string
  allowed_roles: Role[]
  allowed_teams: string[]
  page_count: number
  chunk_count: number
  ingestion_error: string | null
}

export interface Team {
  slug: string
  label: string
  members: MemberRef[]
  documents: DocumentRef[]
  member_count: number
}

export interface AccessEntry {
  document_id: string
  title: string
  department: string
  allowed: boolean
  reason: string | null
}

export interface AccessPreview {
  user: User
  entries: AccessEntry[]
  allowed_count: number
  total_count: number
}

export interface MatrixRow {
  kind: "role" | "team"
  key: string
  label: string
  access: Record<string, boolean>
}

export interface AccessMatrix {
  documents: Doc[]
  rows: MatrixRow[]
}

export interface AuditEvent {
  id: string
  timestamp: string
  actor_email: string
  actor_name: string
  action: string
  target: string
  detail: string
}

export interface Source {
  document_id: string
  title: string
  page: number | null
  excerpt: string
  similarity: number | null
  file_url: string | null
}

export interface ChatAnswer {
  answer: string
  sources: Source[]
}

export interface ConversationMessage {
  id: string
  role: "user" | "assistant"
  content: string
  sources: Source[]
  status: string
  created_at: string
}

export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[]
}

export interface Dashboard {
  documents: number
  users: number
  indexed: number
  questions: number
  activity: AuditEvent[]
}

export interface DailyCount {
  date: string
  count: number
}

export interface LabelCount {
  key: string
  label: string
  count: number
}

export interface Analytics {
  days: number
  total_questions: number
  questions_in_period: number
  active_members: number
  questions_per_day: DailyCount[]
  top_documents: LabelCount[]
  activity_by_team: LabelCount[]
  top_members: LabelCount[]
  alerts: {
    unreachable_documents: DocumentRef[]
    members_without_team: MemberRef[]
    empty_teams: LabelCount[]
  }
}

export const AUDIT_ACTIONS = [
  "LOGIN",
  "QUESTION_ASKED",
  "USER_CREATED",
  "USER_UPDATED",
  "USER_DELETED",
  "DOCUMENT_UPLOADED",
  "DOCUMENT_ACCESS_CHANGED",
  "DOCUMENT_DELETED",
  "TEAM_CREATED",
  "TEAM_DELETED",
] as const

export const ACTION_LABELS: Record<string, string> = {
  LOGIN: "Connexion",
  QUESTION_ASKED: "Question posée",
  USER_CREATED: "Membre créé",
  USER_UPDATED: "Membre modifié",
  USER_DELETED: "Membre supprimé",
  DOCUMENT_UPLOADED: "Document ajouté",
  DOCUMENT_ACCESS_CHANGED: "Accès modifié",
  DOCUMENT_DELETED: "Document supprimé",
  TEAM_CREATED: "Équipe créée",
  TEAM_DELETED: "Équipe supprimée",
}

/** Third person, for the activity feed: "Amélie Martin a posé une question". */
export const ACTION_SENTENCES: Record<string, string> = {
  LOGIN: "s'est connecté",
  QUESTION_ASKED: "a posé une question",
  USER_CREATED: "a créé un membre",
  USER_UPDATED: "a modifié un membre",
  USER_DELETED: "a supprimé un membre",
  DOCUMENT_UPLOADED: "a ajouté un document",
  DOCUMENT_ACCESS_CHANGED: "a modifié un accès",
  DOCUMENT_DELETED: "a supprimé un document",
  TEAM_CREATED: "a créé une équipe",
  TEAM_DELETED: "a supprimé une équipe",
}
