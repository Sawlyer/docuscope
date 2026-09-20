import { useCallback, useEffect, useState } from "react"
import { TriangleAlert } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"

export function LoadingRows({ rows = 5, height = "h-12" }: { rows?: number; height?: string }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className={`${height} w-full`} />
      ))}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed bg-card/50 px-6 py-14 text-center">
      <p className="font-medium">{title}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="space-y-1">
        <p className="font-medium text-destructive">{message}</p>
        {onRetry && (
          <button type="button" className="text-muted-foreground underline underline-offset-4" onClick={onRetry}>
            Réessayer
          </button>
        )}
      </div>
    </div>
  )
}

/** Seven screens do not justify a data layer; this covers load, error and refetch. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    if (!path) return
    setLoading(true)
    api
      .get<T>(path)
      .then((result) => {
        setData(result)
        setError(null)
      })
      .catch((caught: Error) => setError(caught.message))
      .finally(() => setLoading(false))
  }, [path])

  useEffect(reload, [reload])

  return { data, loading, error, reload, setData }
}
