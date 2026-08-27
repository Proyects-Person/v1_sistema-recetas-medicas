import { Download, Edit3, Eye, Filter, RotateCcw, Search, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import StatusBadge from '../components/StatusBadge'
import { api, downloadFile } from '../services/api'
import type { RecipeListItem, Status } from '../types'
import { formatLimaDateTime } from '../utils/date'

function reasonLabel(value?: string | null) {
  const labels: Record<string, string> = {
    analisis_receta: 'Análisis de receta',
    preparacion_magistral: 'Preparación magistral',
    consulta_validacion: 'Consulta/validación',
    otro: 'Otro'
  }
  return labels[value || ''] || value || 'Sin motivo'
}

export default function History() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [date, setDate] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (status) params.set('status', status)
    if (date) params.set('date', date)
    const qs = params.toString()
    const data = await api.get<RecipeListItem[]>(`/recipes${qs ? `?${qs}` : ''}`)
    setRecipes(data)
  }

  useEffect(() => { load().catch(err => setError(err.message)) }, [])

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    load().catch(err => setError(err.message))
  }

  const downloadSummary = async (recipeId: number, code: string) => {
    setError('')
    try {
      await downloadFile(`/recipes/${recipeId}/download`, `${code}.pdf`)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const deleteRecipe = async (recipeId: number, code: string) => {
    if (!confirm(`¿Eliminar la receta ${code}? Esta acción no se puede deshacer.`)) return
    setError('')
    try {
      await api.delete(`/recipes/${recipeId}`)
      await load()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const clearFilters = () => {
    setSearch('')
    setStatus('')
    setDate('')
    setError('')
    api.get<RecipeListItem[]>('/recipes').then(setRecipes).catch(err => setError(err.message))
  }

  const exportCsv = () => {
    const header = ['Código', 'Paciente', 'Edad', 'Teléfono', 'Motivo', 'Texto OCR', 'Fecha Lima', 'Estado', 'Validador', 'Confianza OCR']
    const rows = recipes.map(r => [r.code, r.patient_name || '', r.patient_age || '', r.patient_phone || '', reasonLabel(r.service_reason), r.raw_text || '', formatLimaDateTime(r.created_at), r.status, r.validator_name || '', r.ocr_confidence])
    const csv = [header, ...rows].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'historial_recetas.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page-stack">
      <div className="page-title-row"><div><h1>Historial de Recetas</h1><p>Registro completo de recetas procesadas y validadas</p></div><button className="primary-link" onClick={exportCsv}><Download size={17} /> Exportar</button></div>
      <section className="card history-card">
        <form className="filters" onSubmit={submit}>
          <div className="filter-input"><Search size={17} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar por código, paciente o texto OCR..." /></div>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="">Estado</option>
            <option value="pendiente">Pendiente de carga</option>
            <option value="procesada">Pendiente de validación</option>
            <option value="aprobada">Validada</option>
            <option value="observada">Observada</option>
            <option value="cancelada">Rechazada</option>
          </select>
          <button className="outline-btn"><Filter size={16} /> Filtrar</button>
          <button type="button" className="ghost-btn" onClick={clearFilters}><RotateCcw size={16} /> Limpiar</button>
        </form>
        {error && <div className="error-box">{error}</div>}
        {recipes.length === 0 ? <EmptyState title="Sin resultados" text="Ajusta los filtros o procesa una nueva receta." /> : (
          <div className="table-wrap history-table-wrap">
            <table className="history-table">
              <thead><tr><th>Código</th><th>Paciente</th><th>Motivo</th><th>Fecha</th><th>Estado</th><th>Validador</th><th>Acciones</th></tr></thead>
              <tbody>
                {recipes.map(recipe => <tr key={recipe.id}>
                  <td>{recipe.code}</td>
                  <td><strong>{recipe.patient_name || 'Paciente no registrado'}</strong><span>{recipe.patient_age ? `${recipe.patient_age} años · ` : ''}{recipe.patient_phone ? `Tel. ${recipe.patient_phone} · ` : ''}{recipe.file_name || 'Imagen procesada'}</span></td>
                  <td>{reasonLabel(recipe.service_reason)}</td>
                  <td>{formatLimaDateTime(recipe.created_at)}</td>
                  <td><StatusBadge status={recipe.status as Status} /></td>
                  <td>{recipe.validator_name || 'Pendiente'}</td>
                  <td>
                    <div className="action-icons" aria-label={`Acciones de ${recipe.code}`}>
                      <Link to={`/validation/${recipe.id}?mode=view`} title="Visualizar"><Eye size={16} /></Link>
                      <Link to={`/validation/${recipe.id}?mode=edit`} title="Editar"><Edit3 size={16} /></Link>
                      <button className="icon-link" onClick={() => downloadSummary(recipe.id, recipe.code)} title="Descargar PDF"><Download size={16} /></button>
                      <button className="icon-link danger-icon" onClick={() => deleteRecipe(recipe.id, recipe.code)} title="Borrar"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>)}
              </tbody>
            </table>
          </div>
        )}
        <div className="pagination">Mostrando {recipes.length} registros <button>Anterior</button><button>Siguiente</button></div>
      </section>
    </div>
  )
}
