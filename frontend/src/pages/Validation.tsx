import {
  AlertTriangle,
  CheckCircle2,
  Edit3,
  FileText,
  Lock,
  XCircle
} from 'lucide-react'

import {
  useEffect,
  useState
} from 'react'

import {
  Link,
  useNavigate,
  useParams,
  useSearchParams
} from 'react-router-dom'

import EmptyState from '../components/EmptyState'

import IngredientTable from '../components/IngredientTable'

import {
  api,
  fetchBlobUrl
} from '../services/api'

import type {
  IngredientExtraction,
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
    value === undefined
    || value === null
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

  const labels:
    Record<string, string> = {

      analisis_receta:
        'Análisis de receta',

      preparacion_magistral:
        'Preparar producto magistral',

      consulta_validacion:
        'Consulta/validación farmacéutica',

      otro:
        'Otro'
    }

  return (
    labels[value || '']
    || value
    || 'Sin motivo registrado'
  )
}


/**
 * Permite mostrar recetas antiguas que solamente
 * tengan "composition" y todavía no tengan
 * structured_ingredients.
 */
function structuredFromRecipe(
  recipe: Recipe
): IngredientExtraction[] {

  if (
    recipe.structured_ingredients
    && recipe.structured_ingredients.length > 0
  ) {

    return recipe
      .structured_ingredients
      .map(
        item => ({
          ...item,
          sources:
            item.sources || []
        })
      )
  }


  const composition =
    recipe.composition
    || ''


  return composition
    .split('\n')
    .map(
      line => line.trim()
    )
    .filter(Boolean)
    .map(
      (
        line,
        index
      ) => {

        const match =
          line.match(
            /(\d+(?:[.,]\d+)?\s*%)/
          )

        if (!match) {

          return {
            ingredient:
              line,

            concentration:
              null,

            confidence:
              null,

            sources: [
              'legacy'
            ],

            source_line:
              null,

            line_number:
              index + 1
          }
        }


        const matchIndex =
          match.index ?? 0

        const ingredient =
          line
            .slice(
              0,
              matchIndex
            )
            .trim()
            .replace(
              /[+\-,:;]+$/,
              ''
            )
            .trim()


        return {
          ingredient:
            ingredient || line,

          concentration:
            match[1]
              .replace(
                ',',
                '.'
              ),

          confidence:
            null,

          sources: [
            'legacy'
          ],

          source_line:
            null,

          line_number:
            index + 1
        }
      }
    )
}


export default function Validation() {

  const {
    id
  } = useParams()

  const [
    searchParams
  ] = useSearchParams()

  const navigate =
    useNavigate()


  const isViewMode =
    searchParams.get(
      'mode'
    ) === 'view'


  const [
    recipe,
    setRecipe
  ] = useState<Recipe | null>(
    null
  )


  const [
    queue,
    setQueue
  ] = useState<
    RecipeListItem[]
  >([])


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
    structuredIngredients,
    setStructuredIngredients
  ] = useState<
    IngredientExtraction[]
  >([])


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


  const syncRecipe = (
    data: Recipe
  ) => {

    setRecipe(
      data
    )

    setPatientName(
      data.patient_name || ''
    )

    setPatientAge(
      data.patient_age !== null
      && data.patient_age !== undefined
        ? String(
            data.patient_age
          )
        : ''
    )

    setPatientPhone(
      data.patient_phone || ''
    )

    setServiceReason(
      data.service_reason
      || 'analisis_receta'
    )

    setObservations(
      data.observations || ''
    )

    setStructuredIngredients(
      structuredFromRecipe(
        data
      )
    )
  }


  const loadRecipe = async (
    recipeId: string
  ) => {

    const data =
      await api.get<Recipe>(
        `/recipes/${recipeId}`
      )

    syncRecipe(
      data
    )
  }


  useEffect(
    () => {

      setError('')
      setMessage('')

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


  const suggestions =
    recipe?.dictionary_suggestions
    || []


  const validateData = () => {

    if (!patientName.trim()) {

      setError(
        'El nombre del paciente es obligatorio.'
      )

      return null
    }


    if (!patientAge.trim()) {

      setError(
        'La edad del paciente es obligatoria.'
      )

      return null
    }


    const age =
      Number(
        patientAge
      )


    if (
      !Number.isInteger(
        age
      )
      || age < 0
      || age > 130
    ) {

      setError(
        'La edad del paciente debe ser un número válido entre 0 y 130.'
      )

      return null
    }


    if (
      !/^9\d{8}$/.test(
        patientPhone
      )
    ) {

      setError(
        'El teléfono del paciente debe tener 9 dígitos y comenzar con 9.'
      )

      return null
    }


    const cleanIngredients =
      structuredIngredients
        .map(
          item => ({

            ...item,

            ingredient:
              (
                item.ingredient
                || ''
              ).trim(),

            concentration:
              (
                item.concentration
                || ''
              ).trim()
              || null

          })
        )
        .filter(
          item =>
            item.ingredient
            || item.concentration
        )


    const invalidRow =
      cleanIngredients.find(
        item =>
          !item.ingredient
          && item.concentration
      )


    if (invalidRow) {

      setError(
        'Cada concentración debe estar asociada a un insumo.'
      )

      return null
    }


    return {
      age,
      cleanIngredients
    }
  }


  const persistChanges =
    async () => {

      if (
        !recipe
        || isViewMode
      ) {
        return null
      }


      const validated =
        validateData()


      if (!validated) {
        return null
      }


      const updated =
        await api.put<Recipe>(
          `/recipes/${recipe.id}/data`,
          {
            patient_name:
              patientName.trim(),

            patient_age:
              validated.age,

            patient_phone:
              patientPhone.trim(),

            service_reason:
              serviceReason,

            observations,

            structured_ingredients:
              validated.cleanIngredients
          }
        )


      syncRecipe(
        updated
      )


      return updated
    }


  const save = async () => {

    if (
      !recipe
      || isViewMode
    ) {
      return
    }


    setError('')
    setMessage('')


    try {

      const updated =
        await persistChanges()


      if (!updated) {
        return
      }


      setMessage(
        'Información y receta estructurada actualizadas correctamente.'
      )

    } catch (err: any) {

      setError(
        err?.message
        || 'No se pudieron guardar los cambios.'
      )
    }
  }


  const changeStatus = async (
    action:
      | 'approve'
      | 'observe'
      | 'cancel'
  ) => {

    if (
      !recipe
      || isViewMode
    ) {
      return
    }


    setError('')
    setMessage('')


    try {

      // Primero guarda todos los cambios realizados.
      const saved =
        await persistChanges()


      if (!saved) {
        return
      }


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


      syncRecipe(
        updated
      )


      const messages = {

        approve:
          'Receta aprobada correctamente.',

        observe:
          'Receta marcada como observada correctamente.',

        cancel:
          'Receta rechazada correctamente.'
      }


      setMessage(
        messages[action]
      )

    } catch (err: any) {

      setError(
        err?.message
        || 'No se pudo actualizar el estado de la receta.'
      )
    }
  }


  // =========================================================
  // COLA DE VALIDACIÓN
  // =========================================================

  if (!id) {

    return (

      <div
        className="page-stack"
      >

        <div
          className="page-title-row"
        >

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

          <div
            className="error-box"
          >
            {error}
          </div>

        )}


        <section
          className="card"
        >

          {queue.length === 0 ? (

            <EmptyState
              title="Sin pendientes"
              text="No hay recetas procesadas esperando validación."
            />

          ) : (

            queue.map(
              item => (

                <Link
                  className="recent-row"
                  to={
                    `/validation/${item.id}?mode=edit`
                  }
                  key={item.id}
                >

                  <div
                    className="doc-icon"
                  >
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
                        item.patient_name
                        || 'Paciente no registrado'
                      }

                      {' · '}

                      {
                        reasonLabel(
                          item.service_reason
                        )
                      }

                    </span>

                  </div>


                  <span
                    className="badge badge-procesada"
                  >
                    Pendiente
                  </span>

                </Link>

              )
            )

          )}

        </section>

      </div>

    )
  }


  if (
    error
    && !recipe
  ) {

    return (

      <div
        className="error-box"
      >
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


  // =========================================================
  // RECETA
  // =========================================================

  return (

    <div
      className="page-stack validation-page"
    >

      {/* ENCABEZADO */}

      <div
        className="page-title-row"
      >

        <div>

          <h1>

            {isViewMode
              ? 'Visualización de Receta'
              : 'Validación Farmacéutica'
            }

          </h1>


          <p>

            {isViewMode
              ? 'Consulta de receta sin edición'
              : 'Revisión y corrección de la receta estructurada'
            }

          </p>

        </div>


        <span
          className="confidence"
        >

          Confianza OCR:
          {' '}
          {recipe.ocr_confidence}%

        </span>

      </div>


      {isViewMode && (

        <div
          className="info-box"
        >

          <Lock
            size={16}
          />

          Modo visualización:
          los datos se muestran
          solo para consulta.
          Usa el ícono de editar
          desde Historial para modificar.

        </div>

      )}


      <div
        className="two-cols validation-cols"
      >

        {/* RECETA ORIGINAL */}

        <section
          className="card document-box"
        >

          <h2>
            Receta Original
          </h2>


          {imageUrl ? (

            <img
              src={imageUrl}
              alt={`Receta ${recipe.code}`}
            />

          ) : (

            <div
              className="doc-placeholder"
            >

              <FileText
                size={45}
              />

            </div>

          )}


          <div
            className="doc-caption"
          >

            <FileText
              size={22}
            />

            Imagen cargada

            <br />

            {recipe.file_name}

          </div>

        </section>


        {/* INFORMACIÓN ESTRUCTURADA */}

        <section
          className="card structured-form"
        >

          <h2>
            Datos de la evaluación
          </h2>


          <div
            className="patient-grid patient-grid-4"
          >

            <div>

              <label>
                Paciente *
              </label>

              <input
                disabled={isViewMode}
                value={patientName}
                onChange={
                  event =>
                    setPatientName(
                      event.target.value
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
                disabled={isViewMode}
                value={patientAge}
                onChange={
                  event =>
                    setPatientAge(
                      event.target.value
                        .replace(
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
                disabled={isViewMode}
                value={patientPhone}
                onChange={
                  event =>
                    setPatientPhone(
                      event.target.value
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
                disabled={isViewMode}
                value={serviceReason}
                onChange={
                  event =>
                    setServiceReason(
                      event.target.value
                    )
                }
              >

                <option
                  value="analisis_receta"
                >
                  Análisis de receta
                </option>

                <option
                  value="preparacion_magistral"
                >
                  Preparar producto magistral
                </option>

                <option
                  value="consulta_validacion"
                >
                  Consulta/validación farmacéutica
                </option>

                <option
                  value="otro"
                >
                  Otro
                </option>

              </select>

            </div>

          </div>


          {/* RECETA ESTRUCTURADA */}

          <IngredientTable
            items={
              structuredIngredients
            }
            editable={
              !isViewMode
            }
            onChange={
              setStructuredIngredients
            }
          />


          {/* SUGERENCIAS */}

          {suggestions.length > 0 && (

            <div
              className="suggestions-list"
            >

              <h3>
                Correcciones sugeridas
              </h3>


              {suggestions.map(
                (
                  item,
                  index
                ) => (

                  <div
                    className="suggestion-item"
                    key={
                      `${item.original}-${item.suggestion}-${index}`
                    }
                  >

                    <div>

                      <strong>
                        {item.original}
                      </strong>

                      <span>
                        → {item.suggestion}
                      </span>

                    </div>


                    <small>

                      {
                        item.category
                        || 'término'
                      }

                      {' · '}

                      {
                        formatConfidence(
                          item.confidence
                        )
                      }

                      {item.reason
                        ? ` · ${item.reason}`
                        : ''
                      }

                    </small>

                  </div>

                )
              )}

            </div>

          )}


          {/* OBSERVACIONES */}

          <label>
            Observaciones de validación
          </label>

          <textarea
            name="observations"
            value={observations}
            onChange={
              event =>
                setObservations(
                  event.target.value
                )
            }
            readOnly={isViewMode}
            placeholder="Agregar observaciones técnicas si corresponde..."
          />

        </section>

      </div>


      {/* ACCIONES */}

      {!isViewMode ? (

        <section
          className="validation-actions"
        >

          <h2>
            Acciones de Validación
          </h2>


          <div
            className="button-grid"
          >

            <button
              className="outline-btn"
              onClick={save}
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


          {message && (

            <div
              className="success-box"
            >
              {message}
            </div>

          )}


          {error && (

            <div
              className="error-box"
            >
              {error}
            </div>

          )}


          <div
            className="trace-grid"
          >

            <span>

              Validado por:
              {' '}
              {
                recipe.validator_name
                || 'Pendiente'
              }

            </span>


            <span>

              Fecha y hora:
              {' '}
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

      ) : (

        <section
          className="validation-actions readonly-actions"
        >

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


          <div
            className="trace-grid"
          >

            <span>

              Validador:
              {' '}
              {
                recipe.validator_name
                || 'Pendiente'
              }

            </span>


            <span>

              Fecha y hora:
              {' '}
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

      )}

    </div>
  )
}