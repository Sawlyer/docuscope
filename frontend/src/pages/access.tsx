import { useEffect, useMemo, useState } from "react"
import { Loader2, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/app-shell"
import { ErrorState, LoadingRows, useApi } from "@/components/states"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { ApiError, api } from "@/lib/api"
import { slugify } from "@/lib/format"
import { ROLE_LABELS, type AccessMatrix, type Doc, type MatrixRow, type Role, type Team } from "@/lib/types"

/** Rebuild a document's full access lists from the grid, then send them whole. */
function listsFor(rows: MatrixRow[], documentId: string) {
  return {
    allowed_roles: rows.filter((row) => row.kind === "role" && row.access[documentId]).map((row) => row.key),
    allowed_teams: rows.filter((row) => row.kind === "team" && row.access[documentId]).map((row) => row.key),
  }
}

export default function AccessPage() {
  const { data, loading, error, reload } = useApi<AccessMatrix>("/api/access-matrix")
  const { data: teams, reload: reloadTeams } = useApi<Team[]>("/api/teams")
  const [rows, setRows] = useState<MatrixRow[]>([])
  const [busy, setBusy] = useState<string | null>(null)

  const [creating, setCreating] = useState(false)
  const [team, setTeam] = useState({ slug: "", label: "" })
  const [teamError, setTeamError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<MatrixRow | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (data) setRows(data.rows)
  }, [data])

  const teamsBySlug = useMemo(() => new Map((teams ?? []).map((item) => [item.slug, item])), [teams])

  /** What the cascade will actually cost, named before anyone confirms it. */
  const impact = useMemo(() => {
    if (!pendingDelete) return null
    const target = teamsBySlug.get(pendingDelete.key)
    if (!target) return { members: 0, documents: 0, orphaned: [] as string[] }
    const orphaned = target.members
      .filter((member) => {
        const full = (teams ?? []).flatMap((item) => (item.members.some((m) => m.id === member.id) ? [item.slug] : []))
        return full.length === 1
      })
      .map((member) => member.name)
    return { members: target.members.length, documents: target.documents.length, orphaned }
  }, [pendingDelete, teamsBySlug, teams])

  async function toggle(row: MatrixRow, document: Doc, next: boolean) {
    const cell = `${row.key}:${document.id}`
    const optimistic = rows.map((item) =>
      item.kind === row.kind && item.key === row.key
        ? { ...item, access: { ...item.access, [document.id]: next } }
        : item,
    )
    setRows(optimistic)
    setBusy(cell)
    try {
      await api.patch(`/api/documents/${document.id}/access`, listsFor(optimistic, document.id))
    } catch (caught) {
      setRows(rows)
      toast.error(caught instanceof ApiError ? caught.message : "La modification a été refusée")
    } finally {
      setBusy(null)
    }
  }

  async function createTeam() {
    setSubmitting(true)
    setTeamError(null)
    try {
      await api.post("/api/teams", team)
      toast.success(`Équipe ${team.label} créée`)
      setCreating(false)
      setTeam({ slug: "", label: "" })
      reload()
      reloadTeams()
    } catch (caught) {
      setTeamError(caught instanceof ApiError ? caught.message : "L'équipe n'a pas pu être créée")
    } finally {
      setSubmitting(false)
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.del(`/api/teams/${pendingDelete.key}`)
      toast.success(`Équipe ${pendingDelete.label} supprimée`, {
        description: `${impact?.members ?? 0} membre(s) et ${impact?.documents ?? 0} document(s) mis à jour.`,
      })
      reload()
      reloadTeams()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "L'équipe n'a pas pu être supprimée")
    } finally {
      setDeleting(false)
      setPendingDelete(null)
    }
  }

  const roleRows = rows.filter((row) => row.kind === "role")
  const teamRows = rows.filter((row) => row.kind === "team")

  function renderGroup(label: string, group: MatrixRow[]) {
    if (!data) return null
    return (
      <>
        <tr>
          <th
            colSpan={data.documents.length + 2}
            className="sticky left-0 bg-muted/60 px-4 py-1.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
          >
            {label}
          </th>
        </tr>
        {group.map((row) => (
          <tr key={`${row.kind}-${row.key}`} className="border-t">
            <th
              scope="row"
              className="sticky left-0 z-10 whitespace-nowrap bg-card px-4 py-2 text-left text-sm font-medium"
            >
              {row.kind === "role" ? ROLE_LABELS[row.key as Role] : row.label}
              {row.kind === "team" && <span className="ml-2 text-xs font-normal text-muted-foreground">{row.key}</span>}
            </th>
            {data.documents.map((document) => {
              const cell = `${row.key}:${document.id}`
              return (
                <td key={document.id} className="px-3 py-2 text-center">
                  {busy === cell ? (
                    <Loader2 className="mx-auto size-4 animate-spin text-muted-foreground" />
                  ) : (
                    <Checkbox
                      checked={row.access[document.id] ?? false}
                      onCheckedChange={(next) => void toggle(row, document, next === true)}
                      aria-label={`${row.label} peut consulter ${document.title}`}
                    />
                  )}
                </td>
              )
            })}
            <td className="w-12 px-2 py-2 text-right">
              {row.kind === "team" && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Supprimer l'équipe ${row.label}`}
                  onClick={() => setPendingDelete(row)}
                >
                  <Trash2 className="size-4 text-muted-foreground" />
                </Button>
              )}
            </td>
          </tr>
        ))}
      </>
    )
  }

  return (
    <AppShell
      title="Matrice d'accès"
      description="Toute la règle d'autorisation dans une seule grille."
      actions={
        <Button variant="outline" onClick={() => setCreating(true)}>
          <Plus className="size-4" />
          Nouvelle équipe
        </Button>
      }
    >
      <div className="mx-auto w-full max-w-[96rem] space-y-4">
        {error && <ErrorState message={error} onRetry={reload} />}

        <p className="text-sm text-muted-foreground">
          Un membre atteint un document par son rôle ou par l'une de ses équipes. Cocher une case enregistre
          immédiatement.
        </p>

        {loading || !data ? (
          <LoadingRows rows={8} />
        ) : (
          <div className="overflow-x-auto rounded-lg border bg-card">
            <table className="w-full min-w-[64rem] table-fixed border-collapse">
              <colgroup>
                <col className="w-52" />
                {data.documents.map((document) => <col key={document.id} />)}
                <col className="w-12" />
              </colgroup>
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 bg-card px-4 py-3 text-left text-sm font-medium">Autorise</th>
                  {data.documents.map((document) => (
                    <th key={document.id} className="min-w-0 px-2 py-3 text-center align-bottom">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="block w-full truncate text-xs font-medium">{document.title}</span>
                        </TooltipTrigger>
                        <TooltipContent>
                          {document.title} - {document.department}
                        </TooltipContent>
                      </Tooltip>
                    </th>
                  ))}
                  <th className="w-12" />
                </tr>
              </thead>
              <tbody>
                {renderGroup("Par rôle", roleRows)}
                {renderGroup("Par équipe", teamRows)}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Nouvelle équipe</DialogTitle>
            <DialogDescription>Une équipe vide, à laquelle affecter ensuite membres et documents.</DialogDescription>
          </DialogHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              void createTeam()
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="team-label">Nom</Label>
              <Input
                id="team-label"
                value={team.label}
                onChange={(event) => {
                  const label = event.target.value
                  setTeam({ label, slug: slugify(label) })
                }}
                placeholder="Conception"
                required
                minLength={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="team-slug">Identifiant</Label>
              <Input
                id="team-slug"
                value={team.slug}
                onChange={(event) => setTeam({ ...team, slug: event.target.value })}
                required
                minLength={2}
              />
              {teamError && <p className="text-sm text-destructive">{teamError}</p>}
            </div>

            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="size-4 animate-spin" />}
                Créer
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
            <AlertDialogTitle>Supprimer l'équipe {pendingDelete?.label} ?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <p>
                  {impact?.members ?? 0} membre{(impact?.members ?? 0) > 1 ? "s" : ""} perd
                  {(impact?.members ?? 0) > 1 ? "ent" : ""} cette équipe, et {impact?.documents ?? 0} document
                  {(impact?.documents ?? 0) > 1 ? "s" : ""} perd{(impact?.documents ?? 0) > 1 ? "ent" : ""} cet accès.
                </p>
                {impact?.orphaned.length ? (
                  <p className="text-destructive">
                    {impact.orphaned.join(", ")} n'aura{impact.orphaned.length > 1 ? "ont" : ""} plus aucune équipe.
                  </p>
                ) : null}
                <p>Cette action est irréversible.</p>
              </div>
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
