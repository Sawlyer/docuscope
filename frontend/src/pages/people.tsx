import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Loader2, MoreHorizontal, UserPlus } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/app-shell"
import { AccessPreviewPanel } from "@/components/access-preview"
import { DataTable, type Column } from "@/components/data-table"
import { EmptyState, ErrorState, LoadingRows, useApi } from "@/components/states"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { ApiError, api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { ROLES, ROLE_LABELS, type Role, type Team, type User } from "@/lib/types"

function TeamPicker({
  teams,
  selected,
  onChange,
  idPrefix,
}: {
  teams: Team[]
  selected: string[]
  onChange: (next: string[]) => void
  idPrefix: string
}) {
  if (teams.length === 0) return <p className="text-sm text-muted-foreground">Aucune équipe n'existe encore.</p>
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {teams.map((team) => (
        <div key={team.slug} className="flex items-center gap-2">
          <Checkbox
            id={`${idPrefix}-${team.slug}`}
            checked={selected.includes(team.slug)}
            onCheckedChange={(next) =>
              onChange(next ? [...selected, team.slug] : selected.filter((item) => item !== team.slug))
            }
          />
          <Label htmlFor={`${idPrefix}-${team.slug}`} className="font-normal">
            {team.label}
          </Label>
        </div>
      ))}
    </div>
  )
}

export default function PeoplePage() {
  const { user: me } = useAuth()
  const { data, loading, error, reload } = useApi<User[]>("/api/users")
  const { data: teams, reload: reloadTeams } = useApi<Team[]>("/api/teams")
  const [params, setParams] = useSearchParams()

  const [selected, setSelected] = useState<User | null>(null)
  const [draftRole, setDraftRole] = useState<Role>("EMPLOYEE")
  const [draftTeams, setDraftTeams] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [previewToken, setPreviewToken] = useState(0)

  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "EMPLOYEE" as Role, teams: [] as string[] })
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<User | null>(null)
  const [deleting, setDeleting] = useState(false)

  const teamOptions = useMemo(() => teams ?? [], [teams])
  const teamLabel = (slug: string) => teamOptions.find((team) => team.slug === slug)?.label ?? slug

  function open(member: User) {
    setSelected(member)
    setDraftRole(member.role)
    setDraftTeams([...member.teams])
    setPreviewToken((current) => current + 1)
  }

  function close() {
    setSelected(null)
    if (params.has("member")) {
      params.delete("member")
      setParams(params, { replace: true })
    }
  }

  const requested = params.get("member")
  useEffect(() => {
    if (!requested || !data) return
    const match = data.find((member) => member.id === requested)
    if (match) open(match)
  }, [requested, data])

  const columns: Column<User>[] = [
    {
      key: "name",
      header: "Membre",
      sortValue: (row) => row.name.toLowerCase(),
      cell: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium">
            {row.name}
            {row.id === me?.id && <span className="ml-2 text-xs font-normal text-muted-foreground">vous</span>}
          </p>
          <p className="truncate text-xs text-muted-foreground">{row.email}</p>
        </div>
      ),
    },
    {
      key: "role",
      header: "Rôle",
      sortValue: (row) => row.role,
      cell: (row) => <Badge variant={row.role === "ADMIN" ? "default" : "secondary"}>{ROLE_LABELS[row.role]}</Badge>,
    },
    {
      key: "teams",
      header: "Équipes",
      cell: (row) =>
        row.teams.length === 0 ? (
          <span className="text-sm text-muted-foreground">aucune</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {row.teams.map((team) => (
              <Badge key={team} variant="outline">
                {teamLabel(team)}
              </Badge>
            ))}
          </div>
        ),
    },
    {
      key: "actions",
      header: "",
      className: "w-12",
      cell: (row) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Actions pour ${row.name}`}
              onClick={(event) => event.stopPropagation()}
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" onClick={(event) => event.stopPropagation()}>
            <DropdownMenuItem onClick={() => open(row)}>Modifier les droits</DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onClick={() => setPendingDelete(row)}>
              Supprimer le membre
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  async function save() {
    if (!selected) return
    setSaving(true)
    try {
      const updated = await api.patch<User>(`/api/users/${selected.id}`, { role: draftRole, teams: draftTeams })
      toast.success(`${updated.name} mis à jour`)
      setSelected(updated)
      setPreviewToken((current) => current + 1)
      reload()
      reloadTeams()
    } catch (caught) {
      // The server is the authority on these rules; show its own wording.
      toast.error(caught instanceof ApiError ? caught.message : "La modification a été refusée")
    } finally {
      setSaving(false)
    }
  }

  async function create() {
    setSubmitting(true)
    setFormError(null)
    try {
      const created = await api.post<User>("/api/users", form)
      toast.success(`${created.name} ajouté`, { description: `${ROLE_LABELS[created.role]} - peut se connecter immédiatement.` })
      setCreating(false)
      setForm({ email: "", name: "", password: "", role: "EMPLOYEE", teams: [] })
      reload()
      reloadTeams()
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "Le membre n'a pas pu être créé")
    } finally {
      setSubmitting(false)
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.del(`/api/users/${pendingDelete.id}`)
      toast.success(`${pendingDelete.name} supprimé`)
      if (selected?.id === pendingDelete.id) close()
      reload()
      reloadTeams()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Le membre n'a pas pu être supprimé")
    } finally {
      setDeleting(false)
      setPendingDelete(null)
    }
  }

  return (
    <AppShell
      title="Membres"
      description="Qui est dans quelle équipe, et ce que chacun peut exactement consulter."
      actions={
        <Button onClick={() => setCreating(true)}>
          <UserPlus className="size-4" />
          Ajouter un membre
        </Button>
      }
    >
      <div className="mx-auto max-w-6xl space-y-4">
        {error && <ErrorState message={error} onRetry={reload} />}

        {loading || !data ? (
          <LoadingRows />
        ) : (
          <DataTable
            rows={data}
            columns={columns}
            rowKey={(row) => row.id}
            searchText={(row) => `${row.name} ${row.email} ${row.teams.map(teamLabel).join(" ")}`}
            onRowClick={open}
            filters={[
              {
                key: "role",
                label: "Rôle",
                options: ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] })),
                match: (row, value) => row.role === value,
              },
              {
                key: "team",
                label: "Équipe",
                options: teamOptions.map((team) => ({ value: team.slug, label: team.label })),
                match: (row, value) => row.teams.includes(value),
              },
            ]}
            empty={<EmptyState title="Aucun membre" description="Ajoutez le premier membre de cet espace." />}
          />
        )}
      </div>

      <Sheet open={selected !== null} onOpenChange={(next) => !next && close()}>
        <SheetContent className="flex w-full flex-col sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>{selected?.name}</SheetTitle>
            <SheetDescription>{selected?.email}</SheetDescription>
          </SheetHeader>

          {selected && (
            <div className="flex-1 space-y-6 overflow-y-auto px-4">
              <div className="space-y-2">
                <Label htmlFor="member-role">Rôle</Label>
                <Select value={draftRole} onValueChange={(value) => setDraftRole(value as Role)}>
                  <SelectTrigger id="member-role" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        {ROLE_LABELS[role]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Équipes</Label>
                <TeamPicker teams={teamOptions} selected={draftTeams} onChange={setDraftTeams} idPrefix="edit" />
              </div>

              <Button onClick={() => void save()} disabled={saving} className="w-full">
                {saving && <Loader2 className="size-4 animate-spin" />}
                Enregistrer
              </Button>

              <Separator />

              <div className="space-y-3">
                <p className="text-sm font-medium">Ce que {selected.name.split(" ")[0]} peut consulter</p>
                <AccessPreviewPanel userId={selected.id} refreshToken={previewToken} />
              </div>
            </div>
          )}

          <SheetFooter>
            <Button variant="outline" onClick={() => selected && setPendingDelete(selected)}>
              Supprimer le membre
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ajouter un membre</DialogTitle>
            <DialogDescription>Le compte est utilisable dès sa création.</DialogDescription>
          </DialogHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              void create()
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="new-name">Nom complet</Label>
              <Input
                id="new-name"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
                minLength={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-email">Adresse e-mail</Label>
              <Input
                id="new-email"
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                placeholder="prenom@docuscope.local"
                required
                aria-invalid={formError ? true : undefined}
              />
              {formError && <p className="text-sm text-destructive">{formError}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-password">Mot de passe provisoire</Label>
              <Input
                id="new-password"
                type="text"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                required
                minLength={8}
              />
              <p className="text-xs text-muted-foreground">Au moins 8 caractères.</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-role">Rôle</Label>
              <Select value={form.role} onValueChange={(value) => setForm({ ...form, role: value as Role })}>
                <SelectTrigger id="new-role" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {ROLE_LABELS[role]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Équipes</Label>
              <TeamPicker
                teams={teamOptions}
                selected={form.teams}
                onChange={(next) => setForm({ ...form, teams: next })}
                idPrefix="new"
              />
            </div>

            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="size-4 animate-spin" />}
                Ajouter
              </Button>
              <Button type="button" variant="outline" onClick={() => setCreating(false)}>
                Annuler
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={pendingDelete !== null} onOpenChange={(next) => !next && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer {pendingDelete?.name} ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le compte est supprimé et ses accès révoqués immédiatement. Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault()
                void confirmDelete()
              }}
              disabled={deleting}
            >
              {deleting && <Loader2 className="size-4 animate-spin" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  )
}
