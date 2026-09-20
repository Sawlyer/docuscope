import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowRight, FileStack, FileText, MessagesSquare, Users } from "lucide-react"

import { AppShell } from "@/components/app-shell"
import { ErrorState, LoadingRows, useApi } from "@/components/states"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/auth"
import { absoluteTime, relativeTime } from "@/lib/format"
import { ACTION_SENTENCES, type Dashboard } from "@/lib/types"

function Stat({ icon: Icon, label, value, hint }: { icon: typeof Users; label: string; value: number; hint: string }) {
  return (
    <Card>
      <CardContent className="space-y-1 pt-1">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{label}</p>
          <Icon className="size-4 text-muted-foreground" />
        </div>
        <p className="tabular text-3xl font-semibold tracking-tight">{value}</p>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  )
}

export default function OverviewPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error, reload } = useApi<Dashboard>("/api/dashboard")
  const { data: teamLabels } = useApi<Record<string, string>>("/api/team-labels")
  const [question, setQuestion] = useState("")

  const firstName = user?.name.split(" ")[0] ?? ""

  return (
    <AppShell
      title={`Bonjour ${firstName}`}
      description="Ce que votre compte peut atteindre, et ce qui s'est passé récemment."
    >
      <div className="mx-auto max-w-6xl space-y-6">
        {error && <ErrorState message={error} onRetry={reload} />}

        {loading || !data ? (
          <LoadingRows rows={4} height="h-28" />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Stat
                icon={FileText}
                label="Consultables par vous"
                value={data.documents}
                hint={`sur ${data.indexed} indexés dans l'espace`}
              />
              <Stat
                icon={FileStack}
                label="Documents indexés"
                value={data.indexed}
                hint="Disponibles pour la recherche"
              />
              <Stat icon={Users} label="Membres" value={data.users} hint="Toutes équipes confondues" />
              <Stat
                icon={MessagesSquare}
                label="Questions posées"
                value={data.questions}
                hint="Chacune est journalisée"
              />
            </div>

            <div className="grid items-start gap-4 lg:grid-cols-[1.4fr_1fr]">
              <Card>
                <CardHeader>
                  <CardTitle>Interroger l'espace</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Les réponses s'appuient sur{" "}
                    {data.documents === 1 ? "le document" : `les ${data.documents} documents`} que votre compte est
                    autorisé à consulter.
                  </p>
                </CardHeader>
                <CardContent>
                  <form
                    className="flex flex-col gap-2 sm:flex-row"
                    onSubmit={(event) => {
                      event.preventDefault()
                      navigate("/chat", { state: { question } })
                    }}
                  >
                    <Input
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      placeholder="Qu'est-ce qui a changé dans la politique RH ?"
                      aria-label="Poser une question"
                    />
                    <Button type="submit" disabled={question.trim().length < 2}>
                      Demander
                      <ArrowRight className="size-4" />
                    </Button>
                  </form>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>{user?.role === "ADMIN" ? "Activité récente" : "Votre activité récente"}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.activity.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Rien à afficher pour l'instant.</p>
                  ) : (
                    data.activity.map((event) => (
                      <div key={event.id} className="flex items-start gap-3 text-sm">
                        <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                        <div className="min-w-0 space-y-0.5">
                          <p className="truncate">
                            <span className="font-medium">{event.actor_name}</span>{" "}
                            <span className="text-muted-foreground">
                              {ACTION_SENTENCES[event.action] ?? event.action}
                            </span>
                          </p>
                          <p className="truncate text-xs text-muted-foreground" title={event.target}>
                            {event.target}
                          </p>
                          <p className="text-xs text-muted-foreground" title={absoluteTime(event.timestamp)}>
                            {relativeTime(event.timestamp)}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                  {user?.role === "ADMIN" && (
                    <Button variant="ghost" size="sm" className="w-full" onClick={() => navigate("/audit")}>
                      Ouvrir le journal d'audit
                    </Button>
                  )}
                </CardContent>
              </Card>
            </div>

            {user?.role !== "ADMIN" && <Card>
              <CardHeader>
                <CardTitle>Vos droits</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-2 text-sm">
                {user?.teams.length ? (
                  user.teams.map((team) => (
                    <Badge key={team} variant="outline">
                      {teamLabels?.[team] ?? team}
                    </Badge>
                  ))
                ) : (
                  <span className="text-muted-foreground">Aucune équipe</span>
                )}
                <span className="text-muted-foreground">
                  déterminent les documents accessibles dans la recherche.
                </span>
              </CardContent>
            </Card>}
          </>
        )}
      </div>
    </AppShell>
  )
}
