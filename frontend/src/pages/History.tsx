import {
  Download,
  Edit3,
  Eye,
  Filter,
  Loader2,
  RotateCcw,
  Search,
  Trash2
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import StatusBadge from '../components/StatusBadge'
import { api, downloadFile } from '../services/api'
import type { RecipeListItem } from '../types'
import {
  formatLimaDateTime,
  parseBackendDate
} from '../utils/date'

const PAGE_SIZE = 10

const STATUS_LABELS: Record<string, string> = {
  pendiente: 'Pendiente de carga',
  procesando: 'Procesando',
  procesada: 'Pendiente de validación',
  aprobada: 'Validada',
  observada: 'Observada',
  cancelada: 'Rechazada',
  rechazada: 'Rechazada'
}

function reasonLabel(value?: string | null) {
  const labels: Record<string, string> = {
    analisis_receta: 'Análisis de receta',
    preparacion_magistral: 'Preparar producto magistral',
    consulta_validacion: 'Consulta/validación farmacéutica',
    otro: 'Otro'
  }

  return labels[value || ''] || value || 'Sin motivo'
}

function normalize(value: unknown): string {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

function statusValue(value: string): string {
  const normalized = normalize(value)

  // Compatibilidad con la denominación interna del rechazo.
  return normalized === 'rechazada'
    ? 'cancelada'
    : normalized
}

function limaDateKey(value?: string | null): string {
  const parsed = parseBackendDate(value)

  if (!parsed || Number.isNaN(parsed.getTime())) {
    return ''
  }

  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Lima',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(parsed)

  const part = (type: string) =>
    parts.find(item => item.type === type)?.value || ''

  return `${part('year')}-${part('month')}-${part('day')}`
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message
    ? error.message
    : fallback
}

export default function History() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [date, setDate] = useState('')
  const [page, setPage] = useState(1)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [deletingId, setDeletingId] = useState<number | null>(null)
  const deleteInProgress = useRef(false)

  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [downloadNotice, setDownloadNotice] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const downloadInProgress = useRef(false)

  useEffect(() => {
    let active = true

    const load = async () => {
      setLoading(true)
      setError('')

      try {
        // Obtener el listado completo.
        // Los filtros se aplican debajo de forma consistente.
        const data = await api.get<RecipeListItem[]>('/recipes')

        if (active) {
          setRecipes(data)
        }
      } catch (err: unknown) {
        if (active) {
          setError(
            errorMessage(
              err,
              'No se pudo cargar el historial de recetas.'
            )
          )
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [])

  const filteredRecipes = useMemo(() => {
    const terms = normalize(search)
      .split(' ')
      .filter(Boolean)

    return recipes.filter(recipe => {
      if (
        status &&
        statusValue(recipe.status) !== statusValue(status)
      ) {
        return false
      }

      if (date && limaDateKey(recipe.created_at) !== date) {
        return false
      }

      if (terms.length === 0) {
        return true
      }

      const searchableText = normalize([
        recipe.code,
        recipe.patient_name,
        recipe.patient_age,
        recipe.patient_phone,
        recipe.file_name,
        recipe.composition,
        recipe.doctor_name,
        recipe.service_reason,
        reasonLabel(recipe.service_reason),
        recipe.validator_name,
        STATUS_LABELS[recipe.status] || recipe.status
      ].join(' '))

      // Todas las palabras ingresadas deben estar presentes.
      return terms.every(term => searchableText.includes(term))
    })
  }, [recipes, search, status, date])

  const totalPages = Math.max(
    1,
    Math.ceil(filteredRecipes.length / PAGE_SIZE)
  )

  const currentPage = Math.min(page, totalPages)
  const startIndex = (currentPage - 1) * PAGE_SIZE

  const visibleRecipes = filteredRecipes.slice(
    startIndex,
    startIndex + PAGE_SIZE
  )

  const hasFilters = Boolean(search.trim() || status || date)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setPage(1)
  }

  const clearFilters = () => {
    setSearch('')
    setStatus('')
    setDate('')
    setPage(1)
  }

  const downloadSummary = async (
    recipeId: number,
    code: string
  ) => {
    if (
      downloadInProgress.current ||
      deleteInProgress.current
    ) {
      return
    }

    downloadInProgress.current = true
    setDownloadingId(recipeId)
    setDownloadError('')
    setDownloadNotice(
      `Preparando PDF de la receta ${code}. ` +
      'La descarga comenzará en unos momentos...'
    )

    try {
      await downloadFile(
        `/recipes/${recipeId}/download`,
        `${code}.pdf`
      )

      setDownloadNotice(
        `Se inició la descarga del PDF de la receta ${code}. ` +
        'Revisa las descargas de tu navegador.'
      )
    } catch (err: unknown) {
      setDownloadNotice('')
      setDownloadError(
        errorMessage(
          err,
          `No se pudo descargar el PDF de la receta ${code}.`
        )
      )
    } finally {
      downloadInProgress.current = false
      setDownloadingId(null)
    }
  }

  const deleteRecipe = async (
    recipeId: number,
    code: string
  ) => {
    if (
      deleteInProgress.current ||
      downloadInProgress.current
    ) {
      return
    }

    setError('')
    setSuccess('')

    if (
      !window.confirm(
        `¿Eliminar la receta ${code}? Esta acción no se puede deshacer.`
      )
    ) {
      return
    }

    deleteInProgress.current = true
    setDeletingId(recipeId)

    try {
      await api.delete(`/recipes/${recipeId}`)

      setRecipes(current =>
        current.filter(recipe => recipe.id !== recipeId)
      )

      setSuccess(
        `La receta ${code} se eliminó definitivamente de forma exitosa.`
      )
    } catch (err: unknown) {
      setError(
        errorMessage(
          err,
          'No se pudo eliminar la receta. Inténtalo nuevamente.'
        )
      )
    } finally {
      deleteInProgress.current = false
      setDeletingId(null)
    }
  }

  const exportCsv = () => {
    const header = [
      'Código',
      'Paciente',
      'Edad',
      'Teléfono',
      'Motivo',
      'Receta estructurada',
      'Fecha Lima',
      'Estado',
      'Validador',
      'Confianza'
    ]

    // Exportar todos los resultados filtrados, no solo la página visible.
    const rows = filteredRecipes.map(recipe => [
      recipe.code,
      recipe.patient_name || '',
      recipe.patient_age ?? '',
      recipe.patient_phone || '',
      reasonLabel(recipe.service_reason),
      recipe.composition || '',
      formatLimaDateTime(recipe.created_at),
      STATUS_LABELS[recipe.status] || recipe.status,
      recipe.validator_name || '',
      recipe.ocr_confidence
    ])

    const csv = [header, ...rows]
      .map(row =>
        row
          .map(cell => `"${String(cell).replace(/"/g, '""')}"`)
          .join(',')
      )
      .join('\n')

    const blob = new Blob(['\uFEFF', csv], {
      type: 'text/csv;charset=utf-8'
    })

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = 'historial_recetas.csv'

    document.body.appendChild(link)
    link.click()
    link.remove()

    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <h1>Historial de Recetas</h1>
          <p>
            Registro completo de recetas procesadas y validadas
          </p>
        </div>

        <button
          type="button"
          className="primary-link"
          onClick={exportCsv}
          disabled={loading || filteredRecipes.length === 0}
        >
          <Download size={17} />
          Exportar
        </button>
      </div>

      <div role="status" aria-live="polite" aria-atomic="true">
        {downloadNotice && (
          <div
            className="success-box"
            style={
              downloadingId !== null
                ? {
                    background: '#eff6ff',
                    color: '#1e40af'
                  }
                : undefined
            }
          >
            {downloadingId !== null && (
              <Loader2
                size={17}
                aria-hidden="true"
                style={{
                  verticalAlign: 'middle',
                  marginRight: 8
                }}
              />
            )}
            {downloadNotice}
          </div>
        )}

        {success && (
          <div className="success-box">
            {success}
          </div>
        )}
      </div>

      {downloadError && (
        <div className="error-box" role="alert">
          {downloadError}
        </div>
      )}

      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}

      <section className="card history-card">
        <form className="filters" onSubmit={submit}>
          <div className="filter-input">
            <Search size={17} />

            <input
              aria-label="Buscar recetas"
              value={search}
              onChange={event => {
                setSearch(event.target.value)
                setPage(1)
              }}
              placeholder="Buscar por código, paciente o receta estructurada..."
              disabled={loading}
            />
          </div>

          <input
            type="date"
            aria-label="Fecha de registro en Lima"
            title="Fecha de registro en Lima"
            value={date}
            onChange={event => {
              setDate(event.target.value)
              setPage(1)
            }}
            disabled={loading}
          />

          <select
            aria-label="Estado de la receta"
            value={status}
            onChange={event => {
              setStatus(event.target.value)
              setPage(1)
            }}
            disabled={loading}
          >
            <option value="">Todos los estados</option>
            <option value="pendiente">
              Pendiente de carga
            </option>
            <option value="procesando">
              Procesando
            </option>
            <option value="procesada">
              Pendiente de validación
            </option>
            <option value="aprobada">
              Validada
            </option>
            <option value="observada">
              Observada
            </option>
            <option value="cancelada">
              Rechazada
            </option>
          </select>

          <button
            type="submit"
            className="outline-btn"
            disabled={loading}
          >
            <Filter size={16} />
            Filtrar
          </button>

          <button
            type="button"
            className="ghost-btn"
            onClick={clearFilters}
          >
            <RotateCcw size={16} />
            Limpiar
          </button>
        </form>

        <p className="muted-text">
          Los filtros se aplican automáticamente y se combinan.
          La fecha corresponde al registro de la receta en Lima.
        </p>

        {loading ? (
          <div role="status" aria-live="polite">
            Cargando historial de recetas...
          </div>
        ) : filteredRecipes.length === 0 ? (
          <EmptyState
            title={
              hasFilters
                ? 'Sin resultados para los filtros seleccionados'
                : 'Sin recetas'
            }
            text={
              hasFilters
                ? 'Modifica los filtros o haz clic en Limpiar.'
                : error
                  ? 'No se pudo obtener el historial. Recarga para volver a intentar.'
                  : 'Procesa una receta para verla en el historial.'
            }
          />
        ) : (
          <div className="table-wrap history-table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Paciente</th>
                  <th>Motivo</th>
                  <th>Fecha</th>
                  <th>Estado</th>
                  <th>Validador</th>
                  <th>Acciones</th>
                </tr>
              </thead>

              <tbody>
                {visibleRecipes.map(recipe => {
                  const preparingPdf = downloadingId === recipe.id

                  return (
                    <tr key={recipe.id}>
                      <td>{recipe.code}</td>

                      <td>
                        <strong>
                          {recipe.patient_name || 'Paciente no registrado'}
                        </strong>

                        <span>
                          {recipe.patient_age != null
                            ? `${recipe.patient_age} años · `
                            : ''}

                          {recipe.patient_phone
                            ? `Tel. ${recipe.patient_phone} · `
                            : ''}

                          {recipe.file_name || 'Imagen procesada'}
                        </span>
                      </td>

                      <td>
                        {reasonLabel(recipe.service_reason)}
                      </td>

                      <td>
                        {formatLimaDateTime(recipe.created_at)}
                      </td>

                      <td>
                        <StatusBadge status={recipe.status} />
                      </td>

                      <td>
                        {recipe.validator_name || 'Pendiente'}
                      </td>

                      <td>
                        <div
                          className="action-icons"
                          aria-label={`Acciones de ${recipe.code}`}
                        >
                          <Link
                            to={`/validation/${recipe.id}?mode=view`}
                            title="Visualizar"
                          >
                            <Eye size={16} />
                          </Link>

                          <Link
                            to={`/validation/${recipe.id}?mode=edit`}
                            title="Editar"
                          >
                            <Edit3 size={16} />
                          </Link>

                          <button
                            type="button"
                            className="icon-link"
                            onClick={() =>
                              downloadSummary(recipe.id, recipe.code)
                            }
                            disabled={
                              downloadingId !== null ||
                              deletingId !== null
                            }
                            aria-busy={preparingPdf}
                            aria-label={
                              preparingPdf
                                ? `Preparando PDF de ${recipe.code}`
                                : `Descargar PDF de ${recipe.code}`
                            }
                            title={
                              preparingPdf
                                ? 'Preparando PDF...'
                                : 'Descargar PDF'
                            }
                          >
                            {preparingPdf ? (
                              <>
                                <Loader2 size={16} />
                                <span>Preparando...</span>
                              </>
                            ) : (
                              <Download size={16} />
                            )}
                          </button>

                          <button
                            type="button"
                            className="icon-link danger-icon"
                            onClick={() =>
                              deleteRecipe(recipe.id, recipe.code)
                            }
                            disabled={
                              deletingId !== null ||
                              downloadingId !== null
                            }
                            title={
                              deletingId === recipe.id
                                ? 'Eliminando...'
                                : 'Borrar'
                            }
                            aria-label={`Borrar receta ${recipe.code}`}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loading && (
          <div className="pagination">
            <span role="status" aria-live="polite">
              Mostrando{' '}
              {filteredRecipes.length === 0 ? 0 : startIndex + 1}
              {' a '}
              {Math.min(
                startIndex + PAGE_SIZE,
                filteredRecipes.length
              )}
              {' de '}
              {filteredRecipes.length}
              {' resultados'}
              {hasFilters ? ` (${recipes.length} recetas en total)` : ''}
            </span>

            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() =>
                setPage(Math.max(1, currentPage - 1))
              }
            >
              Anterior
            </button>

            <span>
              Página {currentPage} de {totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() =>
                setPage(Math.min(totalPages, currentPage + 1))
              }
            >
              Siguiente
            </button>
          </div>
        )}
      </section>
    </div>
  )
}