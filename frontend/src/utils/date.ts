export function parseBackendDate(value?: string | null): Date | null {
  if (!value) return null
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

export function formatLimaDateTime(value?: string | null): string {
  const date = parseBackendDate(value)
  if (!date || Number.isNaN(date.getTime())) return 'Pendiente'
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: 'America/Lima',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }).format(date)
}

export function formatLimaDate(value?: string | null): string {
  const date = parseBackendDate(value)
  if (!date || Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: 'America/Lima',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date)
}
