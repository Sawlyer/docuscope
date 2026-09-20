import { useState } from "react"
import { MessagesSquare, Users, UsersRound } from "lucide-react"
import { AppShell } from "@/components/app-shell"
import { ErrorState, LoadingRows, useApi } from "@/components/states"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { longDate, shortDate } from "@/lib/format"
import type { Analytics, LabelCount } from "@/lib/types"

const WINDOWS = [{ value: "7", label: "7 derniers jours" }, { value: "14", label: "14 derniers jours" }, { value: "30", label: "30 derniers jours" }]

function Stat({ icon: Icon, label, value, hint }: { icon: typeof Users; label: string; value: number; hint: string }) {
  return <Card><CardContent className="space-y-1 pt-1"><div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">{label}</p><Icon className="size-4 text-muted-foreground" /></div><p className="tabular text-3xl font-semibold tracking-tight">{value}</p><p className="text-xs text-muted-foreground">{hint}</p></CardContent></Card>
}

function DailyChart({ series }: { series: Analytics["questions_per_day"] }) {
  const peak = Math.max(1, ...series.map((point) => point.count))
  const step = series.length > 20 ? 7 : series.length > 10 ? 3 : 1
  return <div className="flex gap-3"><div className="flex h-40 flex-col justify-between py-0.5 text-[10px] text-muted-foreground"><span>{peak}</span><span>{Math.round(peak / 2)}</span><span>0</span></div><div className="min-w-0 flex-1 space-y-2"><div className="flex h-40 items-end gap-1 border-b">{series.map((point) => <Tooltip key={point.date}><TooltipTrigger asChild><div className="flex h-full flex-1 items-end"><div className="w-full rounded-t-sm bg-primary/85 transition-colors hover:bg-primary" style={{ height: `${Math.max(point.count === 0 ? 2 : 8, (point.count / peak) * 100)}%` }} role="img" aria-label={`${point.count} questions le ${longDate(point.date)}`} /></div></TooltipTrigger><TooltipContent>{point.count} question{point.count > 1 ? "s" : ""} - {longDate(point.date)}</TooltipContent></Tooltip>)}</div><div className="flex gap-1">{series.map((point, index) => <span key={point.date} className="tabular flex-1 text-center text-[10px] text-muted-foreground">{index % step === 0 ? shortDate(point.date) : ""}</span>)}</div></div></div>
}

function Ranking({ rows, empty }: { rows: LabelCount[]; empty: string }) {
  const peak = Math.max(1, ...rows.map((row) => row.count))
  if (!rows.length) return <p className="text-sm text-muted-foreground">{empty}</p>
  return <div className="space-y-2.5">{rows.map((row) => <div key={row.key} className="space-y-1"><div className="flex items-baseline justify-between gap-3 text-sm"><span className="min-w-0 truncate">{row.label}</span><span className="tabular shrink-0 text-muted-foreground">{row.count}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${(row.count / peak) * 100}%` }} /></div></div>)}</div>
}

export default function AnalyticsPage() {
  const [days, setDays] = useState("14")
  const { data, loading, error, reload } = useApi<Analytics>(`/api/analytics?days=${days}`)
  return <AppShell title="Analytique" description="Ce que l'espace sert réellement, et à qui." actions={<Select value={days} onValueChange={setDays}><SelectTrigger className="w-44"><SelectValue /></SelectTrigger><SelectContent>{WINDOWS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select>}><div className="mx-auto max-w-6xl space-y-6">{error && <ErrorState message={error} onRetry={reload} />}{loading || !data ? <LoadingRows rows={3} height="h-28" /> : <><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"><Stat icon={MessagesSquare} label="Questions sur la période" value={data.questions_in_period} hint={`${data.total_questions} depuis le début`} /><Stat icon={UsersRound} label="Membres actifs" value={data.active_members} hint="Au moins une question posée" /><Stat icon={Users} label="Équipes suivies" value={data.activity_by_team.length} hint="Activité comptée par équipe" /></div><Card><CardHeader><CardTitle>Questions par jour</CardTitle><p className="text-sm text-muted-foreground">Sur {data.days} jours.</p></CardHeader><CardContent><DailyChart series={data.questions_per_day} /></CardContent></Card><div className="grid gap-4 lg:grid-cols-3"><Card><CardHeader><CardTitle>Documents les plus cités</CardTitle></CardHeader><CardContent><Ranking rows={data.top_documents} empty="Aucune citation sur la période." /></CardContent></Card><Card><CardHeader><CardTitle>Activité par équipe</CardTitle></CardHeader><CardContent><Ranking rows={data.activity_by_team} empty="Aucune équipe." /></CardContent></Card><Card><CardHeader><CardTitle>Membres les plus actifs</CardTitle></CardHeader><CardContent><Ranking rows={data.top_members} empty="Personne n'a posé de question." /></CardContent></Card></div></>}</div></AppShell>
}
