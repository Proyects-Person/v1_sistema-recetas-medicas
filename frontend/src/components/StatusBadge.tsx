import type { Status } from '../types'

const labels: Record<Status, string> = {
  pendiente: 'Pendiente',
  procesando: 'Procesando',
  procesada: 'Pendiente validación',
  aprobada: 'Validada',
  observada: 'Observada',
  cancelada: 'Rechazada'
}

export default function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge-${status}`}>{labels[status] || status}</span>
}
