import { api } from "./api"
import { conversationsApi } from "./conversations"


test("conversation client uses owner-scoped server endpoints", async () => {
  const post = vi.spyOn(api, "post").mockResolvedValue({ id: "c-1" })
  const get = vi.spyOn(api, "get").mockResolvedValue([])
  const del = vi.spyOn(api, "del").mockResolvedValue(undefined)

  await conversationsApi.list()
  await conversationsApi.create()
  await conversationsApi.get("c-1")
  await conversationsApi.send("c-1", "Bonjour")
  await conversationsApi.remove("c-1")

  expect(get).toHaveBeenNthCalledWith(1, "/api/conversations")
  expect(get).toHaveBeenNthCalledWith(2, "/api/conversations/c-1")
  expect(post).toHaveBeenNthCalledWith(1, "/api/conversations", {})
  expect(post).toHaveBeenNthCalledWith(2, "/api/conversations/c-1/messages", { question: "Bonjour" })
  expect(del).toHaveBeenCalledWith("/api/conversations/c-1")
})
