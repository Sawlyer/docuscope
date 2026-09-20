import { useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Download, ExternalLink, FileWarning, Loader2, Lock, MoreHorizontal, Plus, Upload } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/app-shell"
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
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Switch } from "@/components/ui/switch"
import { ApiError, api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { slugify } from "@/lib/format"
import { ROLES, ROLE_LABELS, type Doc, type Role, type Team } from "@/lib/types"

function AccessSummary({ document, label }: { document: Doc; label: (slug: string) => string }) {
  if (document.allowed_roles.length === 0 && document.allowed_teams.length === 0) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <Lock className="size-3" />
        Personne
      </span>
    )
  }
  return (
    <div className="flex flex-wrap gap-1">
      {document.allowed_roles.map((role) => (
        <Badge key={role} variant="secondary">
          {ROLE_LABELS[role]}
        </Badge>
      ))}
      {document.allowed_teams.map((team) => (
        <Badge key={team} variant="outline">
          {label(team)}
        </Badge>
      ))}
    </div>
  )
}

export default function DocumentsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === "ADMIN"
  const { data, loading, error, reload } = useApi<Doc[]>("/api/documents")
  const { data: teams, reload: reloadTeams } = useApi<Team[]>(isAdmin ? "/api/teams" : null)
  const { data: teamLabels } = useApi<Record<string, string>>("/api/team-labels")
  const [params, setParams] = useSearchParams()
  const [selected, setSelected] = useState<Doc | null>(null)
  const [preview, setPreview] = useState<{ url: string; mimeType: string } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [draftRoles, setDraftRoles] = useState<Role[]>([])
  const [draftTeams, setDraftTeams] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<Doc | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [creatingTeam, setCreatingTeam] = useState(false)
  const [teamDraft, setTeamDraft] = useState({ slug: "", label: "" })
  const [teamError, setTeamError] = useState<string | null>(null)
  const [teamSubmitting, setTeamSubmitting] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const teamList = useMemo(() => teams ?? [], [teams])
  const teamName = (slug: string) =>
    teamList.find((team) => team.slug === slug)?.label ?? teamLabels?.[slug] ?? slug

  function open(document: Doc) {
    setPreview(null)
    setPreviewError(null)
    setPreviewLoading(true)
    setSelected(document)
    setDraftRoles([...document.allowed_roles])
    setDraftTeams([...document.allowed_teams])
  }

  function close() {
    setSelected(null)
    setPreview(null)
    setPreviewError(null)
    setPreviewLoading(false)
    if (params.has("document")) {
      params.delete("document")
      setParams(params, { replace: true })
    }
  }

  useEffect(() => {
    if (!selected) return

    let active = true
    let objectUrl: string | null = null
    void api.blob(`/api/documents/${selected.id}/file`)
      .then((file) => {
        if (!active) return
        objectUrl = URL.createObjectURL(file)
        setPreview({ url: objectUrl, mimeType: file.type })
      })
      .catch((caught) => {
        if (!active) return
        setPreviewError(
          caught instanceof ApiError && caught.status === 404
            ? "Le fichier original n'est pas disponible. Supprimez ce document puis importez-le à nouveau."
            : caught instanceof ApiError
              ? caught.message
              : "Le fichier n'a pas pu être chargé.",
        )
      })
      .finally(() => {
        if (active) setPreviewLoading(false)
      })

    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [selected])

  const requested = params.get("document")
  useEffect(() => {
    if (!requested || !data) return
    const match = data.find((document) => document.id === requested)
    if (match) open(match)
  }, [requested, data])

  const departments = useMemo(
    () => Array.from(new Set((data ?? []).map((document) => document.department))).sort(),
    [data],
  )

  const columns: Column<Doc>[] = [
    {
      key: "title",
      header: "Document",
      sortValue: (row) => row.title.toLowerCase(),
      cell: (row) => <span className="font-medium">{row.title}</span>,
    },
    {
      key: "department",
      header: "Service",
      sortValue: (row) => row.department.toLowerCase(),
      cell: (row) => <span className="text-muted-foreground">{row.department}</span>,
    },
    {
      key: "status",
      header: "État",
      cell: (row) => (
        <div className="space-y-1">
          <Badge variant="secondary">{row.status === "READY" || row.status === "indexed" ? "Indexé" : row.status}</Badge>
          {row.chunk_count > 0 && <p className="text-xs text-muted-foreground">{row.page_count} page{row.page_count > 1 ? "s" : ""} · {row.chunk_count} fragment{row.chunk_count > 1 ? "s" : ""}</p>}
        </div>
      ),
    },
    {
      key: "access",
      header: "Qui peut le consulter",
      cell: (row) => <AccessSummary document={row} label={teamName} />,
    },
  ]

  if (isAdmin) {
    columns.push({
      key: "actions",
      header: "",
      className: "w-12",
      cell: (row) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Actions pour ${row.title}`}
              onClick={(event) => event.stopPropagation()}
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" onClick={(event) => event.stopPropagation()}>
            <DropdownMenuItem onClick={() => open(row)}>Modifier les accès</DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onClick={() => setPendingDelete(row)}>
              Supprimer le document
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    })
  }

  async function upload(file: File) {
    setUploading(true)
    const form = new FormData()
    form.append("file", file)
    try {
      const created = await api.upload<Doc>("/api/documents", form)
      toast.success(`${created.title} indexé`, {
        description: "Seuls les administrateurs y accèdent tant qu'aucun droit n'est accordé.",
      })
      reload()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "L'ajout a échoué")
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ""
    }
  }

  async function saveAccess() {
    if (!selected) return
    setSaving(true)
    try {
      await api.patch<Doc>(`/api/documents/${selected.id}/access`, {
        allowed_roles: draftRoles,
        allowed_teams: draftTeams,
      })
      toast.success("Accès mis à jour", { description: `${selected.title} suit désormais cette sélection.` })
      close()
      reload()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "La modification a été refusée")
    } finally {
      setSaving(false)
    }
  }

  async function createTeam() {
    setTeamSubmitting(true)
    setTeamError(null)
    try {
      const created = await api.post<Team>("/api/teams", teamDraft)
      setDraftTeams((current) => Array.from(new Set([...current, created.slug])))
      setTeamDraft({ slug: "", label: "" })
      setCreatingTeam(false)
      reloadTeams()
      toast.success(`Équipe ${created.label} créée`, {
        description: selected ? "Elle est sélectionnée pour ce document. Enregistrez les accès pour confirmer." : undefined,
      })
    } catch (caught) {
      setTeamError(caught instanceof ApiError ? caught.message : "L'équipe n'a pas pu être créée")
    } finally {
      setTeamSubmitting(false)
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.del(`/api/documents/${pendingDelete.id}`)
      toast.success(`${pendingDelete.title} supprimé`)
      if (selected?.id === pendingDelete.id) close()
      reload()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "La suppression a échoué")
    } finally {
      setDeleting(false)
      setPendingDelete(null)
    }
  }

  const uploadButton = isAdmin && (
    <>
      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.txt,.md"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) void upload(file)
        }}
      />
      <Button onClick={() => fileInput.current?.click()} disabled={uploading}>
        {uploading ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
        Ajouter un document
      </Button>
    </>
  )

  return (
    <AppShell
      title="Documents"
      description={
        isAdmin
          ? "Toutes les sources de l'espace. Ouvrez-en une pour changer qui peut la consulter."
          : "Les documents que votre compte est autorisé à consulter."
      }
      actions={uploadButton}
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
            searchText={(row) => `${row.title} ${row.department}`}
            onRowClick={open}
            filters={[
              {
                key: "department",
                label: "Service",
                options: departments.map((value) => ({ value, label: value })),
                match: (row, value) => row.department === value,
              },
            ]}
            empty={
              <EmptyState
                title={isAdmin ? "Aucun document" : "Rien ne vous est encore partagé"}
                description={
                  isAdmin
                    ? "Ajoutez une source pour la rendre interrogeable par les rôles et équipes que vous autorisez."
                    : "Un administrateur doit ouvrir un document à votre rôle ou à l'une de vos équipes."
                }
                action={uploadButton}
              />
            }
          />
        )}
      </div>

      <Sheet open={selected !== null} onOpenChange={(next) => !next && close()}>
        <SheetContent
          className="flex flex-col gap-0"
          style={{ width: "min(96vw, 80rem)", maxWidth: "min(96vw, 80rem)" }}
        >
          <SheetHeader className="border-b pe-14">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <SheetTitle className="truncate">{selected?.title}</SheetTitle>
                <SheetDescription>
                  {selected?.department} · {selected?.page_count ?? 0} page{selected?.page_count === 1 ? "" : "s"}
                </SheetDescription>
              </div>
              {selected && preview && (
                <div className="flex shrink-0 items-center gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <a href={preview.url} target="_blank" rel="noreferrer">
                      <ExternalLink className="size-4" />
                      Nouvel onglet
                    </a>
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <a href={preview.url} download={selected.title}>
                      <Download className="size-4" />
                      Télécharger
                    </a>
                  </Button>
                </div>
              )}
            </div>
            <SheetDescription>
              {isAdmin ? "Consultez le fichier original et gérez ses accès." : "Fichier original en lecture seule."}
            </SheetDescription>
          </SheetHeader>

          {selected && (
            <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className="relative min-h-[28rem] overflow-hidden bg-muted/30 lg:min-h-0">
                {previewLoading ? (
                  <div className="absolute inset-0 grid place-items-center" role="status">
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <Loader2 className="size-5 animate-spin" />
                      Chargement du fichier original…
                    </div>
                  </div>
                ) : previewError ? (
                  <div className="absolute inset-0 grid place-items-center p-8">
                    <div className="max-w-md space-y-3 text-center">
                      <FileWarning className="mx-auto size-8 text-muted-foreground" />
                      <p className="font-medium">Aperçu indisponible</p>
                      <p className="text-sm leading-6 text-muted-foreground">{previewError}</p>
                    </div>
                  </div>
                ) : preview ? (
                  <iframe
                    src={preview.url}
                    title={`Aperçu de ${selected.title}`}
                    className="h-full min-h-[28rem] w-full bg-white lg:min-h-0"
                  />
                ) : null}
              </div>

              <aside className="space-y-6 overflow-y-auto border-t p-5 lg:border-t-0 lg:border-s">
                {!isAdmin ? (
                  <div className="space-y-3">
                    <p className="font-medium">Vos accès</p>
                    <AccessSummary document={selected} label={teamName} />
                    <p className="text-sm leading-6 text-muted-foreground">
                      Seuls les administrateurs peuvent modifier les accès aux documents.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="space-y-3">
                      <p className="font-medium">Accès par rôle</p>
                      {ROLES.map((role) => (
                        <div key={role} className="flex items-center justify-between">
                          <Label htmlFor={`role-${role}`} className="font-normal">
                            {ROLE_LABELS[role]}
                          </Label>
                          <Switch
                            id={`role-${role}`}
                            checked={draftRoles.includes(role)}
                            onCheckedChange={(next) =>
                              setDraftRoles((current) =>
                                next ? [...current, role] : current.filter((item) => item !== role),
                              )
                            }
                          />
                        </div>
                      ))}
                    </div>

                    <Separator />

                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium">Accès par équipe</p>
                        <Button variant="ghost" size="sm" onClick={() => setCreatingTeam(true)}>
                          <Plus className="size-4" />
                          Nouvelle
                        </Button>
                      </div>
                      {teamList.map((team) => (
                        <div key={team.slug} className="flex items-center justify-between gap-3">
                          <Label htmlFor={`team-${team.slug}`} className="min-w-0 font-normal">
                            <span className="block truncate">{team.label}</span>
                            <span className="tabular text-xs text-muted-foreground">
                              {team.member_count} membre{team.member_count > 1 ? "s" : ""}
                            </span>
                          </Label>
                          <Switch
                            id={`team-${team.slug}`}
                            checked={draftTeams.includes(team.slug)}
                            onCheckedChange={(next) =>
                              setDraftTeams((current) =>
                                next ? [...current, team.slug] : current.filter((item) => item !== team.slug),
                              )
                            }
                          />
                        </div>
                      ))}
                    </div>

                    {draftRoles.length === 0 && draftTeams.length === 0 && (
                      <p className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground">
                        Sans sélection, personne ne pourra consulter ou citer ce document.
                      </p>
                    )}

                    <SheetFooter className="p-0 pt-2">
                      <Button onClick={() => void saveAccess()} disabled={saving}>
                        {saving && <Loader2 className="size-4 animate-spin" />}
                        Enregistrer les accès
                      </Button>
                      <Button variant="outline" onClick={() => setPendingDelete(selected)}>
                        Supprimer le document
                      </Button>
                    </SheetFooter>
                  </>
                )}
              </aside>
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={creatingTeam} onOpenChange={setCreatingTeam}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Nouvelle équipe</DialogTitle>
            <DialogDescription>
              Créez l'équipe puis enregistrez les accès du document pour lui partager ce fichier.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              void createTeam()
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="document-team-label">Nom</Label>
              <Input
                id="document-team-label"
                value={teamDraft.label}
                onChange={(event) => {
                  const label = event.target.value
                  setTeamDraft({ label, slug: slugify(label) })
                }}
                placeholder="Juridique"
                required
                minLength={2}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="document-team-slug">Identifiant</Label>
              <Input
                id="document-team-slug"
                value={teamDraft.slug}
                onChange={(event) => setTeamDraft((current) => ({ ...current, slug: event.target.value }))}
                required
                minLength={2}
              />
              <p className="text-xs leading-5 text-muted-foreground">
                Utilisé dans les règles d'accès. Lettres minuscules, chiffres et tirets recommandés.
              </p>
              {teamError && <p className="text-sm text-destructive">{teamError}</p>}
            </div>
            <DialogFooter>
              <Button type="submit" disabled={teamSubmitting}>
                {teamSubmitting && <Loader2 className="size-4 animate-spin" />}
                Créer et sélectionner
              </Button>
              <Button type="button" variant="outline" onClick={() => setCreatingTeam(false)}>
                Annuler
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={pendingDelete !== null} onOpenChange={(next) => !next && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer {pendingDelete?.title} ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le document sort de l'index et ne pourra plus être cité dans aucune réponse. Cette action est
              irréversible.
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
