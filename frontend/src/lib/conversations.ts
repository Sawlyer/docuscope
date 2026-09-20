import { api } from "@/lib/api"
import type { ConversationDetail, ConversationSummary } from "@/lib/types"

export const conversationsApi = {
  list: () => api.get<ConversationSummary[]>("/api/conversations"),
  get: (id: string) => api.get<ConversationDetail>(`/api/conversations/${id}`),
  create: () => api.post<ConversationSummary>("/api/conversations", {}),
  remove: (id: string) => api.del<void>(`/api/conversations/${id}`),
  send: (id: string, question: string) => api.post<ConversationDetail>(`/api/conversations/${id}/messages`, { question }),
}
