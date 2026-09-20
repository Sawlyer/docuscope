import { useCallback, useEffect, useState } from "react"
import { Check, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { AccessPreview } from "@/lib/types"

// Computed server-side by accessible_documents(), the same function the chat
// endpoint calls before retrieval. This panel cannot drift from the real rule.
export function AccessPreviewPanel({ userId, refreshToken }: { userId: string; refreshToken: number }) {
  const [preview, setPreview] = useState<AccessPreview | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setPreview(null)
    api
      .get<AccessPreview>(`/api/users/${userId}/access`)
      .then((result) => {
        setPreview(result)
        setError(null)
      })
      .catch((caught: Error) => setError(caught.message))
  }, [userId])

  useEffect(load, [load, refreshToken])

  if (error) return <p className="text-sm text-destructive">{error}</p>

  if (!preview) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <p className="text-sm">
          <span className="tabular font-medium">{preview.allowed_count}</span> document
          {preview.allowed_count > 1 ? "s" : ""} consultable{preview.allowed_count > 1 ? "s" : ""} sur{" "}
          <span className="tabular font-medium">{preview.total_count}</span>
        </p>
        <p className="text-xs text-muted-foreground">
          Calculé par la même porte d'autorisation que le chat : c'est exactement ce que verrait le moteur de recherche.
        </p>
      </div>

      <div className="space-y-1.5">
        {preview.entries.map((entry) => (
          <div
            key={entry.document_id}
            className="flex items-center gap-3 rounded-md border bg-background px-3 py-2"
          >
            {entry.allowed ? (
              <Check className="size-4 shrink-0 text-granted" />
            ) : (
              <X className="size-4 shrink-0 text-muted-foreground" />
            )}
            <div className="min-w-0 flex-1">
              <p className={`truncate text-sm ${entry.allowed ? "font-medium" : "text-muted-foreground"}`}>
                {entry.title}
              </p>
              <p className="truncate text-xs text-muted-foreground">{entry.department}</p>
            </div>
            {entry.allowed ? (
              <Badge variant="outline" className="shrink-0 border-granted/40 text-granted">
                {entry.reason}
              </Badge>
            ) : (
              <Badge variant="secondary" className="shrink-0">
                bloqué
              </Badge>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
