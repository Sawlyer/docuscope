import { NavLink } from "react-router-dom"
import { ChartColumn, Files, Grid3x3, LayoutDashboard, MessagesSquare, ScrollText, ShieldCheck, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ThemeToggle } from "@/components/theme-toggle"
import { useAuth } from "@/lib/auth"
import { ROLE_LABELS } from "@/lib/types"
import { cn } from "@/lib/utils"

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  adminOnly: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Accueil", icon: LayoutDashboard, adminOnly: false },
  { to: "/chat", label: "Interroger", icon: MessagesSquare, adminOnly: false },
  { to: "/documents", label: "Documents", icon: Files, adminOnly: false },
  { to: "/membres", label: "Membres", icon: Users, adminOnly: true },
  { to: "/acces", label: "Matrice d'accès", icon: Grid3x3, adminOnly: true },
  { to: "/analytique", label: "Analytique", icon: ChartColumn, adminOnly: true },
  { to: "/audit", label: "Journal d'audit", icon: ScrollText, adminOnly: true },
]

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()
}

export function AppShell({
  title,
  description,
  actions,
  children,
}: {
  title: string
  description?: string
  actions?: React.ReactNode
  children: React.ReactNode
}) {
  const { user, logout } = useAuth()
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "ADMIN")

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-sidebar md:flex">
        <div className="flex items-center gap-2 border-b px-5 py-4">
          <ShieldCheck className="size-5 text-primary" />
          <div className="leading-tight">
            <p className="font-semibold">DocuScope</p>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 p-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  isActive && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b bg-card/80 px-6 py-3.5 backdrop-blur">
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold tracking-tight">{title}</h1>
            {description && <p className="truncate text-sm text-muted-foreground">{description}</p>}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {actions}
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2 px-2">
                  <Avatar className="size-7">
                    <AvatarFallback className="text-xs">{initials(user?.name ?? "?")}</AvatarFallback>
                  </Avatar>
                  <span className="hidden text-sm sm:inline">{user?.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60">
                <DropdownMenuLabel className="space-y-1.5 font-normal">
                  <p className="text-sm font-medium">{user?.name}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                  <div className="flex flex-wrap gap-1 pt-0.5">
                    <Badge variant={user?.role === "ADMIN" ? "default" : "secondary"}>
                      {user ? ROLE_LABELS[user.role] : ""}
                    </Badge>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>Se déconnecter</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  )
}
