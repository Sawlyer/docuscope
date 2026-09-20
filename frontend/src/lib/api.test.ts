import { request, setUnauthorizedHandler } from "./api"


test("requests use browser credentials without authorization headers", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } }),
  )

  await request("POST", "/api/example", { value: 1 })

  expect(fetchMock).toHaveBeenCalledWith("/api/example", expect.objectContaining({ credentials: "include" }))
  const options = fetchMock.mock.calls[0][1] as RequestInit
  expect(new Headers(options.headers).has("Authorization")).toBe(false)
})


test("a 401 notifies the authentication provider", async () => {
  const unauthorized = vi.fn()
  setUnauthorizedHandler(unauthorized)
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "expired" }), { status: 401, headers: { "Content-Type": "application/json" } }),
  )

  await expect(request("GET", "/api/auth/me")).rejects.toMatchObject({ status: 401 })
  expect(unauthorized).toHaveBeenCalledOnce()
})
