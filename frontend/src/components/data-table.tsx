import { useMemo, useState } from "react"
import { ArrowDown, ArrowUp, ChevronsUpDown, Search } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"

export interface Column<T> {
  key: string
  header: string
  cell: (row: T) => React.ReactNode
  sortValue?: (row: T) => string | number
  className?: string
}

export interface Filter<T> {
  key: string
  label: string
  options: { value: string; label: string }[]
  match: (row: T, value: string) => boolean
}

export function DataTable<T>({
  columns,
  rows,
  searchText,
  filters = [],
  empty,
  onRowClick,
  rowKey,
}: {
  columns: Column<T>[]
  rows: T[]
  searchText: (row: T) => string
  filters?: Filter<T>[]
  empty: React.ReactNode
  onRowClick?: (row: T) => void
  rowKey: (row: T) => string
}) {
  const [query, setQuery] = useState("")
  const [sort, setSort] = useState<{ key: string; direction: 1 | -1 } | null>(null)
  const [active, setActive] = useState<Record<string, string>>({})

  const visible = useMemo(() => {
    let result = rows
    const needle = query.trim().toLowerCase()
    if (needle) result = result.filter((row) => searchText(row).toLowerCase().includes(needle))
    for (const filter of filters) {
      const value = active[filter.key]
      if (value && value !== "all") result = result.filter((row) => filter.match(row, value))
    }
    if (sort) {
      const column = columns.find((item) => item.key === sort.key)
      if (column?.sortValue) {
        const read = column.sortValue
        result = [...result].sort((a, b) => {
          const left = read(a)
          const right = read(b)
          if (left === right) return 0
          return (left > right ? 1 : -1) * sort.direction
        })
      }
    }
    return result
  }, [rows, query, sort, active, columns, filters, searchText])

  const filtersAreOn = query.trim() !== "" || Object.values(active).some((value) => value && value !== "all")

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Rechercher..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Rechercher dans ce tableau"
          />
        </div>
        {filters.map((filter) => (
          <Select
            key={filter.key}
            value={active[filter.key] ?? "all"}
            onValueChange={(value) => setActive((current) => ({ ...current, [filter.key]: value }))}
          >
            <SelectTrigger className="w-48">
              <SelectValue placeholder={filter.label} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{filter.label} : tout</SelectItem>
              {filter.options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ))}
        <span className="tabular text-sm text-muted-foreground">
          {visible.length} sur {rows.length}
        </span>
      </div>

      {visible.length === 0 ? (
        filtersAreOn ? (
          <div className="rounded-lg border border-dashed px-6 py-12 text-center text-sm text-muted-foreground">
            Aucun résultat pour ces filtres.
          </div>
        ) : (
          empty
        )
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    className={cn("whitespace-nowrap", column.className, column.sortValue && "cursor-pointer select-none")}
                    onClick={() => {
                      if (!column.sortValue) return
                      setSort((current) =>
                        current?.key === column.key
                          ? { key: column.key, direction: current.direction === 1 ? -1 : 1 }
                          : { key: column.key, direction: 1 },
                      )
                    }}
                  >
                    <span className="inline-flex items-center gap-1">
                      {column.header}
                      {column.sortValue &&
                        (sort?.key !== column.key ? (
                          <ChevronsUpDown className="size-3 opacity-40" />
                        ) : sort.direction === 1 ? (
                          <ArrowUp className="size-3" />
                        ) : (
                          <ArrowDown className="size-3" />
                        ))}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((row) => (
                <TableRow
                  key={rowKey(row)}
                  className={cn(onRowClick && "cursor-pointer")}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {columns.map((column) => (
                    <TableCell key={column.key} className={column.className}>
                      {column.cell(row)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
