import { useEffect, useRef, useState } from "react"
import { useLocation } from "react-router-dom"
import { ChevronDown, Loader2, MessageSquare, Plus, Send, ShieldCheck, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { AppShell } from "@/components/app-shell"
import { useApi } from "@/components/states"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, api } from "@/lib/api"
import { conversationsApi } from "@/lib/conversations"
import type { ChatAnswer, ConversationDetail, ConversationSummary, Dashboard, Source } from "@/lib/types"

interface Exchange {
  question: string
  answer: ChatAnswer | null
}

const SUGGESTIONS = [
  "Qu'est-ce qui a changé dans la politique RH ?",
  "Comment l'accès à distance est-il sécurisé ?",
  "Comment a évolué le chiffre d'affaires ?",
]

function SourceRow({ index, source }: { index: number; source: Source }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-md border bg-background">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        <Badge variant="outline" className="tabular">
          {index}
        </Badge>
        <span className="min-w-0 flex-1 truncate font-medium">{source.title}{source.page ? ` · page ${source.page}` : ""}</span>
        <ChevronDown
          className={`size-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="space-y-2 border-t px-3 py-2">
          <p className="text-sm text-muted-foreground">{source.excerpt}</p>
          <div className="flex items-center justify-between gap-3">
            {source.similarity != null && <span className="text-xs text-muted-foreground">Pertinence {Math.round(source.similarity * 100)} %</span>}
            {source.file_url && (
              <Button variant="outline" size="sm" onClick={async () => {
                try {
                  const file = await api.blob(source.file_url!)
                  const url = URL.createObjectURL(file)
                  window.open(`${url}#page=${source.page ?? 1}`, "_blank", "noopener,noreferrer")
                  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
                } catch (error) {
                  toast.error(error instanceof ApiError ? error.message : "Document indisponible")
                }
              }}>Ouvrir le document</Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ChatPage() {
  const location = useLocation() as { state?: { question?: string } }
  const { data: dashboard } = useApi<Dashboard>("/api/dashboard")
  const [question, setQuestion] = useState("")
  const [pending, setPending] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [active, setActive] = useState<ConversationDetail | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  const seeded = useRef(false)
  const messages = active?.messages ?? []
  const thread: Exchange[] = []
  for (let index = 0; index < messages.length; index += 2) {
    const userMessage = messages[index]
    const assistantMessage = messages[index + 1]
    if (userMessage?.role === "user") {
      thread.push({
        question: userMessage.content,
        answer: assistantMessage?.role === "assistant" ? { answer: assistantMessage.content, sources: assistantMessage.sources } : null,
      })
    }
  }

  async function refreshConversations(preferredId?: string) {
    const items = await conversationsApi.list()
    setConversations(items)
    const nextId = preferredId ?? activeId ?? items[0]?.id ?? null
    setActiveId(nextId)
    if (nextId) setActive(await conversationsApi.get(nextId))
    else setActive(null)
  }

  useEffect(() => {
    void refreshConversations().catch((error) => toast.error(error instanceof ApiError ? error.message : "Conversations indisponibles"))
    // Initial server hydration only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function selectConversation(id: string) {
    setActiveId(id)
    setActive(await conversationsApi.get(id))
  }

  async function newConversation() {
    const conversation = await conversationsApi.create()
    setConversations((current) => [conversation, ...current])
    setActiveId(conversation.id)
    setActive({ ...conversation, messages: [] })
    setQuestion("")
    return conversation.id
  }

  async function deleteConversation(id: string) {
    await conversationsApi.remove(id)
    const remaining = conversations.filter((conversation) => conversation.id !== id)
    setConversations(remaining)
    if (id === activeId) {
      const nextId = remaining[0]?.id ?? null
      setActiveId(nextId)
      setActive(nextId ? await conversationsApi.get(nextId) : null)
    }
    toast.success("Conversation supprimée")
  }

  async function ask(text: string) {
    const trimmed = text.trim()
    if (trimmed.length < 2 || pending) return
    const conversationId = activeId ?? await newConversation()
    setQuestion("")
    setPending(true)
    try {
      const detail = await conversationsApi.send(conversationId, trimmed)
      setActive(detail)
      setConversations((current) => [detail, ...current.filter((item) => item.id !== detail.id)])
    } catch (error) {
      setQuestion(trimmed)
      toast.error(error instanceof ApiError ? error.message : "La question n'a pas pu aboutir")
    } finally {
      setPending(false)
    }
  }

  // A question typed on the home page arrives through router state.
  useEffect(() => {
    const seed = location.state?.question
    if (seed && !seeded.current) {
      seeded.current = true
      void ask(seed)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" })
  }, [thread])

  return (
    <AppShell title="Interroger l'espace" description="Chaque réponse cite les documents qu'elle avait le droit de lire.">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
        <div className="grid items-start gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="space-y-4 rounded-xl border bg-card p-4 lg:sticky lg:top-6">
            <Button className="h-10 w-full justify-center" onClick={() => void newConversation()}>
              <Plus className="mr-2 size-4" /> Nouvelle conversation
            </Button>
            <div className="space-y-1.5">
              {conversations.length === 0 ? (
                <p className="px-2 py-3 text-xs text-muted-foreground">Aucune conversation</p>
              ) : conversations.map((conversation) => (
                <div key={conversation.id} className={`group flex min-h-10 items-center gap-1 rounded-lg ${conversation.id === activeId ? "bg-muted" : "hover:bg-muted/60"}`}>
                  <button type="button" className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left text-sm" onClick={() => void selectConversation(conversation.id)}>
                    <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate">{conversation.title}</span>
                  </button>
                  <Button variant="ghost" size="icon" className="mr-1 size-7 opacity-60 hover:opacity-100" onClick={() => void deleteConversation(conversation.id)} aria-label={`Supprimer ${conversation.title}`}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          </aside>

          <div className="min-w-0 space-y-5">
          <div className="flex items-center justify-between gap-3">
          <p className="truncate text-sm font-medium">{active?.title ?? "Nouvelle conversation"}</p>
          <Button
            variant="ghost"
            size="sm"
            disabled={!activeId || pending}
            onClick={() => activeId && void deleteConversation(activeId)}
          >
            <Trash2 className="mr-2 size-4" /> Supprimer
          </Button>
        </div>
        <div className="flex items-center gap-2 rounded-lg border bg-granted-surface px-3 py-2 text-sm">
          <ShieldCheck className="size-4 shrink-0 text-granted" />
          {dashboard ? (
            <span>
              <span className="tabular font-medium">{dashboard.documents}</span> document
              {dashboard.documents > 1 ? "s" : ""} autorisé{dashboard.documents > 1 ? "s" : ""} pour votre compte sur{" "}
              <span className="tabular font-medium">{dashboard.indexed}</span> indexés. Les autres sont écartés avant
              même la recherche.
            </span>
          ) : (
            <Skeleton className="h-4 w-72" />
          )}
        </div>

        {thread.length === 0 && (
          <Card>
            <CardContent className="space-y-3 pt-1">
              <p className="text-sm text-muted-foreground">Par exemple :</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((suggestion) => (
                  <Button key={suggestion} variant="outline" size="sm" onClick={() => void ask(suggestion)}>
                    {suggestion}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {thread.map((exchange, index) => (
          <div key={index} className="space-y-3">
            <div className="flex justify-end">
              <p className="max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground">
                {exchange.question}
              </p>
            </div>

            <Card>
              <CardContent className="space-y-4 pt-1">
                {exchange.answer === null ? (
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                ) : (
                  <>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{exchange.answer.answer}</p>
                    {exchange.answer.sources.length > 0 ? (
                      <div className="space-y-2">
                        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Sources transmises au modèle
                        </p>
                        {exchange.answer.sources.map((source, position) => (
                          <SourceRow
                            key={source.document_id}
                            index={position + 1}
                            source={source}
                          />
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Aucun document autorisé ne correspond à cette question : rien n'a été transmis au modèle.
                      </p>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        ))}

        <div ref={bottom} />

        <form
          className="sticky bottom-0 flex items-end gap-2 rounded-lg border bg-card p-2"
          onSubmit={(event) => {
            event.preventDefault()
            void ask(question)
          }}
        >
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                void ask(question)
              }
            }}
            placeholder="Posez votre question..."
            rows={2}
            className="min-h-0 resize-none border-0 shadow-none focus-visible:ring-0"
            aria-label="Votre question"
          />
          <Button type="submit" size="icon" disabled={pending || question.trim().length < 2} aria-label="Envoyer">
            {pending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </Button>
        </form>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
