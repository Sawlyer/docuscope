export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Called on any 401 so an expired token cannot leave the app half signed in. */
let onUnauthorized: () => void = () => {}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

function messageFrom(payload: unknown): string {
  const detail = (payload as { detail?: unknown } | null)?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg ?? "Invalid value").join(", ")
  }
  return "Something went wrong."
}

export async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "include",
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
  })

  if (response.status === 401) {
    onUnauthorized()
    throw new ApiError(401, "Your session expired. Please sign in again.")
  }

  if (response.status === 204) return undefined as T

  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, messageFrom(payload))
  return payload as T
}

async function blob(path: string): Promise<Blob> {
  const response = await fetch(path, { credentials: "include" })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(response.status, messageFrom(payload))
  }
  return response.blob()
}

export const api = {
  get: <T,>(path: string) => request<T>("GET", path),
  post: <T,>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T,>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  del: <T,>(path: string) => request<T>("DELETE", path),
  upload: <T,>(path: string, form: FormData) => request<T>("POST", path, undefined, form),
  blob,
}
