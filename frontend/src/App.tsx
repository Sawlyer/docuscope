import { lazy, Suspense } from "react"
import { Navigate, Route, Routes } from "react-router-dom"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { RequireAdmin, RequireAuth } from "@/lib/auth"
const AccessPage = lazy(() => import("@/pages/access"))
const AnalyticsPage = lazy(() => import("@/pages/analytics"))
const AuditPage = lazy(() => import("@/pages/audit"))
const ChatPage = lazy(() => import("@/pages/chat"))
const DocumentsPage = lazy(() => import("@/pages/documents"))
const LoginPage = lazy(() => import("@/pages/login"))
const OverviewPage = lazy(() => import("@/pages/overview"))
const PeoplePage = lazy(() => import("@/pages/people"))

function Protected({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  return <RequireAuth>{admin ? <RequireAdmin>{children}</RequireAdmin> : children}</RequireAuth>
}

export default function App() {
  return (
    <TooltipProvider delayDuration={200}>
      <Suspense fallback={null}><Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Protected><OverviewPage /></Protected>} />
        <Route path="/chat" element={<Protected><ChatPage /></Protected>} />
        <Route path="/documents" element={<Protected><DocumentsPage /></Protected>} />
        <Route path="/membres" element={<Protected admin><PeoplePage /></Protected>} />
        <Route path="/acces" element={<Protected admin><AccessPage /></Protected>} />
        <Route path="/analytique" element={<Protected admin><AnalyticsPage /></Protected>} />
        <Route path="/audit" element={<Protected admin><AuditPage /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></Suspense>
      {/* Bottom right: the side sheets open on the right edge, and a top-right
          toast would cover their header exactly when it reports on them. */}
      <Toaster richColors position="bottom-right" />
    </TooltipProvider>
  )
}
