import { useState } from "react"
import { Navigate, useLocation, useNavigate } from "react-router-dom"
import { Loader2, ShieldCheck } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { ROLE_LABELS } from "@/lib/types"

const ADMIN_ROUTES = ["/membres", "/acces", "/analytique", "/audit"]

const DEMO = [
  {
    email: "admin@docuscope.local",
    password: "Admin123!",
    name: "Amélie Martin",
    role: "ADMIN" as const,
    note: "Administration complète de l'espace",
  },
  {
    email: "lea@docuscope.local",
    password: "Demo123!",
    name: "Léa Bernard",
    role: "EMPLOYEE" as const,
    note: "Documents RH uniquement",
  },
  {
    email: "marc@docuscope.local",
    password: "Demo123!",
    name: "Marc Dubois",
    role: "EMPLOYEE" as const,
    note: "Documents financiers uniquement",
  },
]

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  // RequireAuth parks the page they asked for here; send them back to it.
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/"
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [pending, setPending] = useState<string | null>(null)

  async function submit(nextEmail: string, nextPassword: string, marker: string) {
    setPending(marker)
    try {
      const account = await login(nextEmail, nextPassword)
      // An EMPLOYEE bounced off an admin route must not be sent back into it.
      const restricted = ADMIN_ROUTES.some((route) => from.startsWith(route))
      navigate(restricted && account.role !== "ADMIN" ? "/" : from, { replace: true })
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Connexion impossible")
    } finally {
      setPending(null)
    }
  }

  // Already signed in: send them where they meant to go.
  if (user) return <Navigate to={from} replace />

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-slate-950 p-12 text-white lg:flex">
        <img
          src="/login-security.png"
          alt=""
          aria-hidden
          className="absolute inset-0 size-full object-cover object-center opacity-90"
        />
        <div aria-hidden className="absolute inset-0 bg-[linear-gradient(180deg,rgba(3,12,25,0.32),rgba(3,10,22,0.88))]" />
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(circle_at_78%_48%,rgba(88,213,255,0.16),transparent_34%)]" />
        <div className="relative flex items-center gap-2 font-semibold">
          <ShieldCheck className="size-5" />
          DocuScope
        </div>

        <div className="relative" aria-hidden="true" />
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-8">
          <div className="space-y-1.5">
            <h2 className="text-2xl font-semibold tracking-tight">Connexion</h2>
            <p className="text-sm text-muted-foreground">
              Choisissez un compte de démonstration, ou saisissez vos identifiants.
            </p>
          </div>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              void submit(email, password, "form")
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="email">Adresse e-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                placeholder="vous@entreprise.fr"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={pending !== null}>
              {pending === "form" && <Loader2 className="size-4 animate-spin" />}
              Se connecter
            </Button>
          </form>

          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Comptes de démonstration
              </span>
              <span className="h-px flex-1 bg-border" />
            </div>

            {DEMO.map((account) => (
              <Card
                key={account.email}
                role="button"
                tabIndex={0}
                aria-label={`Se connecter en tant que ${account.name}`}
                onClick={() => void submit(account.email, account.password, account.email)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault()
                    void submit(account.email, account.password, account.email)
                  }
                }}
                className="cursor-pointer p-3 transition-colors hover:border-primary/50 hover:bg-accent focus-visible:border-primary focus-visible:outline-none"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 truncate text-sm font-medium">
                      {account.name}
                      {pending === account.email && <Loader2 className="size-3 animate-spin" />}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">{account.note}</p>
                  </div>
                  <Badge variant={account.role === "ADMIN" ? "default" : "secondary"}>
                    {ROLE_LABELS[account.role]}
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
