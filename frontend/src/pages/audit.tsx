import { useMemo } from "react"

import { AppShell } from "@/components/app-shell"
import { DataTable, type Column } from "@/components/data-table"
import { EmptyState, ErrorState, LoadingRows, useApi } from "@/components/states"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { absoluteTime, relativeTime } from "@/lib/format"
import { ACTION_LABELS, AUDIT_ACTIONS, type AuditEvent, type Team, type User } from "@/lib/types"

const DESTRUCTIVE = new Set(["USER_DELETED", "DOCUMENT_DELETED", "TEAM_DELETED"])
const SENSITIVE = new Set(["DOCUMENT_ACCESS_CHANGED", "USER_UPDATED", "USER_CREATED", "TEAM_CREATED"])

function actionVariant(action: string) {
  if (DESTRUCTIVE.has(action)) return "destructive" as const
  if (SENSITIVE.has(action)) return "default" as const
  return "secondary" as const
}

export default function AuditPage() {
  const { data, loading, error, reload } = useApi<AuditEvent[]>("/api/audit")
  const { data: members } = useApi<User[]>("/api/users")
  const { data: teams } = useApi<Team[]>("/api/teams")

  // An event belongs to a team when its actor does; nothing extra to fetch.
  const teamsByEmail = useMemo(() => {
    const map = new Map<string, string[]>()
    for (const member of members ?? []) map.set(member.email, member.teams)
    return map
  }, [members])

  const columns: Column<AuditEvent>[] = [
    {
      key: "timestamp",
      header: "Quand",
      sortValue: (row) => row.timestamp,
      className: "w-36",
      cell: (row) => (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-sm text-muted-foreground">{relativeTime(row.timestamp)}</span>
          </TooltipTrigger>
          <TooltipContent>{absoluteTime(row.timestamp)}</TooltipContent>
        </Tooltip>
      ),
    },
    {
      key: "actor",
      header: "Auteur",
      sortValue: (row) => row.actor_name.toLowerCase(),
      cell: (row) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{row.actor_name}</p>
          <p className="truncate text-xs text-muted-foreground">{row.actor_email}</p>
        </div>
      ),
    },
    {
      key: "team",
      header: "Équipes",
      sortValue: (row) => (teamsByEmail.get(row.actor_email) ?? []).join(" "),
      cell: (row) => {
        const slugs = teamsByEmail.get(row.actor_email) ?? []
        if (slugs.length === 0) return <span className="text-sm text-muted-foreground">-</span>
        const label = (slug: string) => (teams ?? []).find((team) => team.slug === slug)?.label ?? slug
        return (
          <div className="flex flex-wrap gap-1">
            {slugs.map((slug) => (
              <Badge key={slug} variant="outline">
                {label(slug)}
              </Badge>
            ))}
          </div>
        )
      },
    },
    {
      key: "action",
      header: "Action",
      sortValue: (row) => row.action,
      cell: (row) => <Badge variant={actionVariant(row.action)}>{ACTION_LABELS[row.action] ?? row.action}</Badge>,
    },
    {
      key: "target",
      header: "Cible",
      className: "max-w-64",
      cell: (row) => (
        <span className="block truncate text-sm" title={row.target}>
          {row.target}
        </span>
      ),
    },
    {
      key: "detail",
      header: "Détail",
      className: "max-w-80",
      cell: (row) => (
        <span className="block truncate text-sm text-muted-foreground" title={row.detail}>
          {row.detail || "-"}
        </span>
      ),
    },
  ]

  return (
    <AppShell
      title="Journal d'audit"
      description="Chaque connexion, question, changement de droit et suppression, du plus récent au plus ancien."
    >
      <div className="mx-auto max-w-6xl space-y-4">
        {error && <ErrorState message={error} onRetry={reload} />}

        {loading || !data ? (
          <LoadingRows rows={8} />
        ) : (
          <DataTable
            rows={data}
            columns={columns}
            rowKey={(row) => row.id}
            searchText={(row) => `${row.actor_name} ${row.actor_email} ${row.target} ${row.detail}`}
            filters={[
              {
                key: "team",
                label: "Équipe",
                options: (teams ?? []).map((team) => ({ value: team.slug, label: team.label })),
                match: (row, value) => (teamsByEmail.get(row.actor_email) ?? []).includes(value),
              },
              {
                key: "action",
                label: "Action",
                options: AUDIT_ACTIONS.map((action) => ({ value: action, label: ACTION_LABELS[action] ?? action })),
                match: (row, value) => row.action === value,
              },
              {
                key: "actor",
                label: "Auteur",
                options: (members ?? []).map((member) => ({ value: member.email, label: member.name })),
                match: (row, value) => row.actor_email === value,
              },
            ]}
            empty={
              <EmptyState
                title="Aucun événement"
                description="Les connexions, questions et changements de droits apparaîtront ici au fil de l'eau."
              />
            }
          />
        )}
      </div>
    </AppShell>
  )
}
