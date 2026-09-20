/** Relative timestamps without pulling in a date library. */
export function relativeTime(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  const steps: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, "minute"],
    [60, "hour"],
    [24, "day"],
    [7, "week"],
  ]

  let value = seconds
  let unit: Intl.RelativeTimeFormatUnit = "second"
  for (const [size, next] of steps) {
    if (Math.abs(value) < size) break
    value = Math.round(value / size)
    unit = next
  }
  return new Intl.RelativeTimeFormat("fr", { numeric: "auto" }).format(-value, unit)
}

export function absoluteTime(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" })
}

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })
}

export function longDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })
}

/** French plural agreement, for the one-space-before-s cases we actually hit. */
export function plural(count: number, singular: string, pluralForm?: string): string {
  return count > 1 ? (pluralForm ?? `${singular}s`) : singular
}

/** "Ressources Humaines" -> "ressources-humaines". Accents are stripped by
 *  decomposing, then dropping the combining marks by code point. */
export function slugify(value: string): string {
  const stripped = Array.from(value.normalize("NFD"))
    .filter((character) => {
      const code = character.codePointAt(0) ?? 0
      return code < 0x0300 || code > 0x036f
    })
    .join("")
  return stripped
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}
