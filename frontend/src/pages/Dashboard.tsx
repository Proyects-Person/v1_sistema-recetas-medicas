import { AlertCircle, CheckCircle, Clock3, FileText, UploadCloud } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { api } from '../services/api'
import type { DashboardData } from '../types'
import { formatLimaDateTime } from '../utils/date'

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<DashboardData>('/dashboard').then(setData).catch(err => setError(err.message))
  }, [])

  if (error) return <div className="error-box">{error}</div>
  if (!data) return <div>Cargando panel principal...</div>

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div><h1>Panel Principal</h1><p>Bienvenido al sistema de interpretación de recetas magistrales</p></div>
        <Link className="primary-link" to="/upload"><UploadCloud size={17} /> Subir Nueva Receta</Link>
      </div>
      <section className="stats-grid">
        <Link to="/validation" className="stat-link stat-alert"><StatCard icon={Clock3} helper="Para revisar" value={data.pending} title="Pendientes de validación" /></Link>
        <StatCard icon={CheckCircle} helper="Esta semana" value={data.processed_week} title="Recetas procesadas" />
        <StatCard icon={AlertCircle} helper="Requieren atención" value={data.observed} title="Recetas observadas" />
        <StatCard icon={FileText} helper="Promedio OCR" value={`${data.avg_confidence || 0}%`} title="Confianza promedio" />
      </section>
      <div className="dashboard-grid">
        <section className="card">
          <h2>Recetas recientes</h2>
          {data.recent_recipes.length === 0 ? <EmptyState title="Sin recetas" text="Sube una receta para iniciar el flujo." /> : data.recent_recipes.map(r => (
            <Link to={r.status === 'procesada' ? `/validation/${r.id}?mode=edit` : `/history`} className="recent-row" key={r.id}>
              <div className="doc-icon"><FileText size={16} /></div>
              <div><strong>{r.code}</strong><span>{r.patient_name || formatLimaDateTime(r.created_at)}</span></div>
              <StatusBadge status={r.status} />
            </Link>
          ))}
        </section>
        <section className="card">
          <h2>Actividad de validación</h2>
          <div className="activity-list">
            {data.activities.length === 0 ? <EmptyState title="Sin actividad de validación" text="Aquí aparecerán recetas pendientes, correcciones y cambios de estado." /> : data.activities.map(a => <div className="activity-item" key={a.id}><span></span><div><strong>{a.action}</strong><small>{formatLimaDateTime(a.created_at)}</small><p>{a.description}</p></div></div>)}
          </div>
        </section>
      </div>
    </div>
  )
}
