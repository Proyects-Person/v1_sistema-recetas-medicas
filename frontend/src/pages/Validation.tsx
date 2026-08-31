import {
  AlertTriangle,
  CheckCircle2,
  Edit3,
  FileText,
  Lightbulb,
  Lock,
  Sparkles,
  XCircle
} from 'lucide-react'

import {
  ChangeEvent,
  useEffect,
  useMemo,
  useState
} from 'react'

import {
  Link,
  useNavigate,
  useParams,
  useSearchParams
} from 'react-router-dom'

import EmptyState from '../components/EmptyState'

import {
  api,
  fetchBlobUrl
} from '../services/api'

import type {
  Recipe,
  RecipeListItem
} from '../types'

import {
  formatLimaDateTime
} from '../utils/date'


function formatConfidence(
  value?: number | null
) {
  if (
    value === undefined ||
    value === null
  ) {
    return ''
  }

  const percent =
    value <= 1
      ? value * 100
      : value

  return `${percent.toFixed(0)}%`
}


function reasonLabel(
  value?: string | null
) {
  const labels: Record<string, string> = {
    analisis_receta: 'Análisis de receta',
    preparacion_magistral: 'Preparar producto magistral',
    consulta_validacion: 'Consulta/validación farmacéutica',
    otro: 'Otro'
  }

  return (
    labels[value || ''] ||
    value ||
    'Sin motivo registrado'
  )
}


function structuredValue(
  value?: string | null
) {
  const cleanValue = (
    value || ''
  ).trim()

  return cleanValue || '—'
}


export default function Validation() {

  const {
    id
  } = useParams()

  const [
    searchParams
  ] = useSearchParams()

  const navigate = useNavigate()

  const isViewMode =
    searchParams.get('mode') === 'view'


  // ============================================================
  // ESTADOS
  // ============================================================

  const [
    recipe,
    setRecipe
  ] = useState<Recipe | null>(
    null
  )

  const [
    queue,
    setQueue
  ] = useState<RecipeListItem[]>(
    []
  )

  const [
    rawText,
    setRawText
  ] = useState('')

  const [
    patientName,
    setPatientName
  ] = useState('')

  const [
    patientAge,
    setPatientAge
  ] = useState('')

  const [
    patientPhone,
    setPatientPhone
  ] = useState('')

  const [
    serviceReason,
    setServiceReason
  ] = useState(
    'analisis_receta'
  )

  const [
    observations,
    setObservations
  ] = useState('')

  const [
    message,
    setMessage
  ] = useState('')

  const [
    error,
    setError
  ] = useState('')

  const [
    imageUrl,
    setImageUrl
  ] = useState('')


  // ============================================================
  // CARGAR RECETA
  // ============================================================

  const loadRecipe = async (
    recipeId: string
  ) => {

    const data =
      await api.get<Recipe>(
        `/recipes/${recipeId}`
      )

    setRecipe(
      data
    )

    setRawText(
      data.raw_text || ''
    )

    setPatientName(
      data.patient_name || ''
    )

    setPatientAge(
      data.patient_age !== null &&
      data.patient_age !== undefined
        ? String(
            data.patient_age
          )
        : ''
    )

    setPatientPhone(
      data.patient_phone || ''
    )

    setServiceReason(
      data.service_reason ||
      'analisis_receta'
    )

    setObservations(
      data.observations || ''
    )
  }


  // ============================================================
  // CARGA INICIAL
  // ============================================================

  useEffect(
    () => {

      setError('')

      if (id) {

        loadRecipe(
          id
        ).catch(
          err =>
            setError(
              err.message
            )
        )

      } else {

        api
          .get<RecipeListItem[]>(
            '/recipes?status=procesada'
          )
          .then(
            setQueue
          )
          .catch(
            err =>
              setError(
                err.message
              )
          )
      }

    },
    [id]
  )


  // ============================================================
  // IMAGEN
  // ============================================================

  useEffect(
    () => {

      let activeUrl = ''

      if (!recipe) {
        return undefined
      }

      fetchBlobUrl(
        `/recipes/${recipe.id}/file`
      )
        .then(
          url => {

            activeUrl =
              url

            setImageUrl(
              url
            )
          }
        )
        .catch(
          () =>
            setImageUrl('')
        )

      return () => {

        if (activeUrl) {
          URL.revokeObjectURL(
            activeUrl
          )
        }
      }

    },
    [recipe?.id]
  )


  // ============================================================
  // TEXTO OCR
  // ============================================================

  const updateText = (
    event:
      ChangeEvent<HTMLTextAreaElement>
  ) => {

    setRawText(
      event.target.value
    )
  }


  // ============================================================
  // DATOS DERIVADOS
  // ============================================================

  const suggestions =
    recipe?.dictionary_suggestions ||
    []

  const recognizedTerms =
    recipe?.recognized_terms ||
    []

  const structuredData =
    recipe?.structured_data ||
    []


  // ============================================================
  // TEXTO SUGERIDO
  // ============================================================

  const hasSuggestedText =
    useMemo(
      () => {

        const suggested = (
          recipe?.normalized_text ||
          ''
        ).trim()

        return (
          suggestions.length > 0 &&
          Boolean(
            suggested &&
            suggested !==
              (
                rawText ||
                ''
              ).trim()
          )
        )

      },
      [
        recipe?.normalized_text,
        rawText,
        suggestions.length
      ]
    )


  const useSuggestedText =
    () => {

      if (
        !recipe?.normalized_text ||
        isViewMode
      ) {
        return
      }

      setRawText(
        recipe.normalized_text
      )

      setMessage(
        'Se copió el texto sugerido al campo editable. Guarda los cambios para recalcular los datos estructurados.'
      )
    }


  // ============================================================
  // GUARDAR
  // ============================================================

  const save = async () => {

    if (
      !recipe ||
      isViewMode
    ) {
      return
    }

    setError('')
    setMessage('')


    if (
      !patientName.trim()
    ) {

      setError(
        'El nombre del paciente es obligatorio.'
      )

      return
    }


    if (
      !patientAge.trim()
    ) {

      setError(
        'La edad del paciente es obligatoria.'
      )

      return
    }


    if (
      !/^\d{9}$/.test(
        patientPhone
      )
    ) {

      setError(
        'El teléfono del paciente debe contener exactamente 9 dígitos.'
      )

      return
    }


    try {

      const updated =
        await api.put<Recipe>(
          `/recipes/${recipe.id}/data`,
          {
            raw_text:
              rawText,

            patient_name:
              patientName.trim(),

            patient_age:
              Number(
                patientAge
              ),

            patient_phone:
              patientPhone,

            service_reason:
              serviceReason,

            observations:
              observations
          }
        )


      setRecipe(
        updated
      )

      setRawText(
        updated.raw_text ||
        ''
      )

      setPatientName(
        updated.patient_name ||
        ''
      )

      setPatientAge(
        updated.patient_age !== null &&
        updated.patient_age !== undefined
          ? String(
              updated.patient_age
            )
          : ''
      )

      setPatientPhone(
        updated.patient_phone ||
        ''
      )

      setServiceReason(
        updated.service_reason ||
        'analisis_receta'
      )

      setObservations(
        updated.observations ||
        ''
      )


      setMessage(
        'Información actualizada correctamente. Los datos estructurados fueron recalculados a partir del texto OCR guardado.'
      )

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo guardar la información.'
      )
    }
  }


  // ============================================================
  // CAMBIAR ESTADO
  // ============================================================

  const changeStatus =
    async (
      action:
        | 'approve'
        | 'observe'
        | 'cancel'
    ) => {

      if (
        !recipe ||
        isViewMode
      ) {
        return
      }

      setError('')
      setMessage('')

      try {

        const endpoints = {
          approve:
            'approve',

          observe:
            'observe',

          cancel:
            'cancel'
        }


        const updated =
          await api.post<Recipe>(
            `/recipes/${recipe.id}/${endpoints[action]}`,
            {
              observations
            }
          )


        setRecipe(
          updated
        )

        setMessage(
          'Estado actualizado correctamente.'
        )

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : 'No se pudo actualizar el estado.'
        )
      }
    }


  // ============================================================
  // COLA DE VALIDACIÓN
  // ============================================================

  if (!id) {

    return (

      <div className="page-stack">

        <div className="page-title-row">

          <div>

            <h1>
              Validación Farmacéutica
            </h1>

            <p>
              Recetas procesadas pendientes de validación
            </p>

          </div>

        </div>


        {error && (

          <div className="error-box">
            {error}
          </div>

        )}


        <section className="card">

          {
            queue.length === 0
              ? (

                <EmptyState
                  title="Sin pendientes"
                  text="No hay recetas procesadas esperando validación."
                />

              )
              : (

                queue.map(
                  item => (

                    <Link
                      className="recent-row"
                      to={`/validation/${item.id}?mode=edit`}
                      key={item.id}
                    >

                      <div className="doc-icon">

                        <FileText
                          size={16}
                        />

                      </div>


                      <div>

                        <strong>
                          {item.code}
                        </strong>

                        <span>

                          {
                            item.patient_name ||
                            'Paciente no registrado'
                          }

                          {' · '}

                          {
                            reasonLabel(
                              item.service_reason
                            )
                          }

                        </span>

                      </div>


                      <span className="badge badge-procesada">
                        Pendiente
                      </span>

                    </Link>
                  )
                )
              )
          }

        </section>

      </div>
    )
  }


  // ============================================================
  // CARGANDO
  // ============================================================

  if (
    error &&
    !recipe
  ) {

    return (
      <div className="error-box">
        {error}
      </div>
    )
  }


  if (!recipe) {

    return (
      <div>
        Cargando receta...
      </div>
    )
  }


  const low =
    new Set(
      recipe.low_confidence_fields ||
      []
    )


  // ============================================================
  // VISTA
  // ============================================================

  return (

    <div className="page-stack validation-page">


      {/* ======================================================
          TÍTULO
      ====================================================== */}

      <div className="page-title-row">

        <div>

          <h1>

            {
              isViewMode
                ? 'Visualización de Receta'
                : 'Validación Farmacéutica'
            }

          </h1>

          <p>

            {
              isViewMode
                ? 'Consulta de receta sin edición'
                : 'Revisión de los datos farmacoterapéuticos estructurados y del texto detectado por OCR'
            }

          </p>

        </div>


        <span className="confidence">

          Confianza OCR:{' '}

          {
            recipe.ocr_confidence
          }%

        </span>

      </div>


      {/* ======================================================
          MODO LECTURA
      ====================================================== */}

      {
        isViewMode && (

          <div className="info-box">

            <Lock
              size={16}
            />

            Modo visualización:
            los datos se muestran
            solo para consulta.
            Usa el ícono de editar
            desde Historial para
            modificar.

          </div>
        )
      }


      {/* ======================================================
          RECETA + DATOS GENERALES
      ====================================================== */}

      <div className="two-cols validation-cols">


        {/* RECETA ORIGINAL */}

        <section className="card document-box">

          <h2>
            Receta Original
          </h2>


          {
            imageUrl
              ? (

                <img
                  src={imageUrl}
                  alt={`Receta ${recipe.code}`}
                />

              )
              : (

                <div className="doc-placeholder">

                  <FileText
                    size={45}
                  />

                </div>
              )
          }


          <div className="doc-caption">

            <FileText
              size={22}
            />

            Imagen cargada

            <br />

            {
              recipe.file_name
            }

          </div>

        </section>


        {/* DATOS DE EVALUACIÓN */}

        <section className="card structured-form">

          <h2>
            Datos de la evaluación
          </h2>


          <div className="patient-grid patient-grid-4">


            <div>

              <label>
                Paciente *
              </label>

              <input
                disabled={
                  isViewMode
                }
                value={
                  patientName
                }
                onChange={
                  e =>
                    setPatientName(
                      e.target.value
                    )
                }
                placeholder="Nombre del paciente"
              />

            </div>


            <div>

              <label>
                Edad *
              </label>

              <input
                disabled={
                  isViewMode
                }
                value={
                  patientAge
                }
                onChange={
                  e =>
                    setPatientAge(
                      e.target.value.replace(
                        /[^0-9]/g,
                        ''
                      )
                    )
                }
                inputMode="numeric"
                placeholder="Edad"
              />

            </div>


            <div>

              <label>
                Teléfono *
              </label>

              <input
                disabled={
                  isViewMode
                }
                value={
                  patientPhone
                }
                onChange={
                  e =>
                    setPatientPhone(
                      e.target.value
                        .replace(
                          /[^0-9]/g,
                          ''
                        )
                        .slice(
                          0,
                          9
                        )
                    )
                }
                inputMode="numeric"
                maxLength={9}
                placeholder="987654321"
              />

            </div>


            <div>

              <label>
                Motivo *
              </label>

              <select
                disabled={
                  isViewMode
                }
                value={
                  serviceReason
                }
                onChange={
                  e =>
                    setServiceReason(
                      e.target.value
                    )
                }
              >

                <option value="analisis_receta">
                  Análisis de receta
                </option>

                <option value="preparacion_magistral">
                  Preparar producto magistral
                </option>

                <option value="consulta_validacion">
                  Consulta/validación farmacéutica
                </option>

                <option value="otro">
                  Otro
                </option>

              </select>

            </div>

          </div>


          {/* RESUMEN */}

          <div className="processing-summary">

            <h3>
              Resumen del procesamiento
            </h3>


            <div className="engine-row">

              <span>

                Motor OCR:{' '}

                {
                  recipe.ocr_engine ||
                  'no definido'
                }

              </span>


              {
                structuredData.length > 0 && (

                  <span>

                    {
                      structuredData.length
                    } insumo(s)
                    estructurado(s)

                  </span>
                )
              }


              {
                suggestions.length > 0 ||
                recognizedTerms.length > 0
                  ? (

                    <span>
                      Diccionario farmacéutico activo
                    </span>

                  )
                  : (

                    <span>
                      Sin coincidencias del diccionario
                    </span>

                  )
              }

            </div>


            {
              low.has(
                'raw_text'
              ) && (

                <div className="field-alert">

                  <AlertTriangle
                    size={15}
                  />

                  Baja confianza OCR.
                  Revisa manualmente
                  la transcripción.

                </div>
              )
            }

          </div>


          {/* OBSERVACIONES */}

          <label>
            Observaciones de validación
          </label>

          <textarea
            name="observations"
            value={
              observations
            }
            onChange={
              e =>
                setObservations(
                  e.target.value
                )
            }
            readOnly={
              isViewMode
            }
            placeholder="Agregar observaciones técnicas si corresponde..."
          />

        </section>

      </div>


      {/* ======================================================
          DATA ESTRUCTURADA
      ====================================================== */}

      <section className="card structured-data-card">


        <div className="structured-data-heading">

          <div>

            <h2>
              Datos farmacoterapéuticos estructurados
            </h2>

            <p>

              Información interpretada
              por el backend a partir
              del OCR, reglas Regex y
              diccionario farmacéutico.

              {' '}

              Los campos no identificados
              se muestran como “—”.

            </p>

          </div>


          <span className="structured-count">

            {
              structuredData.length
            } registro(s)

          </span>

        </div>


        {
          structuredData.length > 0
            ? (

              <div className="structured-table-wrap">

                <table className="structured-data-table">

                  <thead>

                    <tr>

                      <th>
                        Medicamento o insumo
                      </th>

                      <th>
                        Concentración
                      </th>

                      <th>
                        Forma farmacéutica
                      </th>

                      <th>
                        Cantidad
                      </th>

                      <th>
                        Dosis
                      </th>

                      <th>
                        Frecuencia
                      </th>

                      <th>
                        Duración
                      </th>

                      <th>
                        Vía de administración
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {
                      structuredData.map(
                        (
                          row,
                          index
                        ) => (

                          <tr
                            key={
                              `${
                                row.medication_or_ingredient ||
                                'insumo'
                              }-${index}`
                            }
                          >

                            <td className="medication-cell">

                              {
                                structuredValue(
                                  row.medication_or_ingredient
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.concentration
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.pharmaceutical_form
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.quantity
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.dosage
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.frequency
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.duration
                                )
                              }

                            </td>


                            <td>

                              {
                                structuredValue(
                                  row.administration_route
                                )
                              }

                            </td>

                          </tr>
                        )
                      )
                    }

                  </tbody>

                </table>

              </div>

            )
            : (

              <div className="structured-data-empty">

                <FileText
                  size={22}
                />

                <div>

                  <strong>
                    No se generaron datos farmacoterapéuticos estructurados.
                  </strong>

                  <span>

                    Revisa el texto OCR
                    y vuelve a guardar
                    la receta para ejecutar
                    nuevamente el parser.

                  </span>

                </div>

              </div>
            )
        }

      </section>


      {/* ======================================================
          TEXTO OCR
      ====================================================== */}

      <section className="card ocr-review-card">


        <h2>
          Texto detectado por OCR
        </h2>


        <p className="muted-text">

          Este texto se conserva
          como evidencia de la
          transcripción.

          {' '}

          Si lo corriges y guardas,
          el backend recalculará
          nuevamente los datos
          estructurados.

        </p>


        <textarea
          name="raw_text"
          className="ocr-textarea"
          value={
            rawText
          }
          onChange={
            updateText
          }
          readOnly={
            isViewMode
          }
          placeholder="Aquí aparecerá todo el texto detectado por OCR..."
        />


        {/* ==================================================
            DICCIONARIO
        ================================================== */}

        {
          suggestions.length > 0 && (

            <div className="dictionary-panel">


              <div className="dictionary-header">

                <div>

                  <h3>

                    <Sparkles
                      size={16}
                    />

                    Sugerencia por diccionario

                  </h3>

                  <p>
                    Úsala solo si coincide
                    visualmente con la receta.
                  </p>

                </div>


                {
                  hasSuggestedText &&
                  !isViewMode && (

                    <button
                      className="outline-btn"
                      onClick={
                        useSuggestedText
                      }
                      type="button"
                    >

                      <Lightbulb
                        size={15}
                      />

                      Usar sugerencia

                    </button>
                  )
                }

              </div>


              {
                recipe.normalized_text
                  ? (

                    <pre>
                      {
                        recipe.normalized_text
                      }
                    </pre>

                  )
                  : (

                    <span className="muted-text">

                      Se detectaron coincidencias,
                      pero no se reemplazó el texto
                      automáticamente.

                    </span>
                  )
              }

            </div>
          )
        }


        {/* ==================================================
            CORRECCIONES SUGERIDAS
        ================================================== */}

        {
          suggestions.length > 0 && (

            <div className="suggestions-list">

              <h3>
                Correcciones sugeridas
              </h3>


              {
                suggestions.map(
                  (
                    item,
                    index
                  ) => (

                    <div
                      className="suggestion-item"
                      key={
                        `${
                          item.original
                        }-${
                          item.suggestion
                        }-${index}`
                      }
                    >

                      <div>

                        <strong>
                          {
                            item.original
                          }
                        </strong>

                        <span>
                          → {
                            item.suggestion
                          }
                        </span>

                      </div>


                      <small>

                        {
                          item.category ||
                          'término'
                        }

                        {' · '}

                        {
                          formatConfidence(
                            item.confidence
                          )
                        }

                        {' · '}

                        {
                          item.reason
                        }

                      </small>

                    </div>
                  )
                )
              }

            </div>
          )
        }


        {/* ==================================================
            TÉRMINOS RECONOCIDOS
        ================================================== */}

        {
          recognizedTerms.length > 0 && (

            <div className="term-tags">

              {
                recognizedTerms
                  .slice(
                    0,
                    10
                  )
                  .map(
                    (
                      item,
                      index
                    ) => (

                      <span
                        key={
                          `${
                            item.term
                          }-${index}`
                        }
                      >

                        {
                          item.term
                        }

                      </span>
                    )
                  )
              }

            </div>
          )
        }

      </section>


      {/* ======================================================
          ACCIONES
      ====================================================== */}

      {
        !isViewMode
          ? (

            <section className="validation-actions">


              <h2>
                Acciones de Validación
              </h2>


              <div className="button-grid">


                <button
                  className="outline-btn"
                  onClick={
                    save
                  }
                >

                  <Edit3
                    size={16}
                  />

                  Guardar cambios

                </button>


                <button
                  className="success-btn"
                  onClick={
                    () =>
                      changeStatus(
                        'approve'
                      )
                  }
                >

                  <CheckCircle2
                    size={16}
                  />

                  Aprobar

                </button>


                <button
                  className="warning-btn"
                  onClick={
                    () =>
                      changeStatus(
                        'observe'
                      )
                  }
                >

                  <AlertTriangle
                    size={16}
                  />

                  Observar

                </button>


                <button
                  className="danger-btn"
                  onClick={
                    () =>
                      changeStatus(
                        'cancel'
                      )
                  }
                >

                  <XCircle
                    size={16}
                  />

                  Rechazar

                </button>

              </div>


              {
                message && (

                  <div className="success-box">
                    {
                      message
                    }
                  </div>
                )
              }


              {
                error && (

                  <div className="error-box">
                    {
                      error
                    }
                  </div>
                )
              }


              <div className="trace-grid">

                <span>

                  Validado por:{' '}

                  {
                    recipe.validator_name ||
                    'Pendiente'
                  }

                </span>


                <span>

                  Fecha y hora:{' '}

                  {
                    formatLimaDateTime(
                      recipe.validated_at
                    )
                  }

                </span>


                <span>
                  Trazabilidad activa
                </span>

              </div>

            </section>

          )
          : (

            <section className="validation-actions readonly-actions">


              <button
                className="outline-btn"
                onClick={
                  () =>
                    navigate(
                      '/history'
                    )
                }
              >

                Volver al historial

              </button>


              <div className="trace-grid">

                <span>

                  Validador:{' '}

                  {
                    recipe.validator_name ||
                    'Pendiente'
                  }

                </span>


                <span>

                  Fecha y hora:{' '}

                  {
                    formatLimaDateTime(
                      recipe.validated_at
                    )
                  }

                </span>


                <span>
                  Modo consulta
                </span>

              </div>

            </section>
          )
      }

    </div>
  )
}