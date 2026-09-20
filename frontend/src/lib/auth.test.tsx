import { render, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { AuthProvider } from "./auth"


test("authentication bootstrap removes legacy JWT storage", async () => {
  localStorage.setItem("docuscope.token", "legacy-jwt")
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "unauthenticated" }), { status: 401, headers: { "Content-Type": "application/json" } }),
  )

  render(<MemoryRouter><AuthProvider><div>app</div></AuthProvider></MemoryRouter>)

  await waitFor(() => expect(localStorage.getItem("docuscope.token")).toBeNull())
})
