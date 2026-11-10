import { FileText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fetchBlobUrl, getToken } from '../services/api'
import type { Recipe } from '../types'

type Stage = 'esperando' | 'imagen' | 'ocr' | 'pln' | 'finalizado'

type ProcessingEvent = {
  stage: Stage | 'error'
  progress: number
  message: string
  recipe?: Recipe
}

const stages = [
  {
    key: 'imagen',
    label: 'Procesamiento de imagen'
  },
  {
    key: 'ocr',
    label: 'Extracción OCR'
  },
  {
    key: 'pln',
    label: 'Estructuración PLN'
  }
] as const

export default function Processing() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState<Stage>('esperando')
  const [statusMessage, setStatusMessage] = useState(
    'Iniciando procesamiento...'
  )
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [imageUrl, setImageUrl] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id || id === '0') {
      return
    }

    let active = true

    api.get<Recipe>(`/recipes/${id}`)
      .then(result => {
        if (active) {
          setRecipe(result)
        }
      })
      .catch(err => {
        if (active) {
          setError(err.message)
        }
      })

    return () => {
      active = false
    }
  }, [id])

  useEffect(() => {
    if (!recipe) {
      return
    }

    let active = true
    let activeUrl = ''

    setImageUrl('')

    fetchBlobUrl(`/recipes/${recipe.id}/file`)
      .then(url => {
        if (!active) {
          URL.revokeObjectURL(url)
          return
        }

        activeUrl = url
        setImageUrl(url)
      })
      .catch(() => {
        if (active) {
          setImageUrl('')
        }
      })

    return () => {
      active = false

      if (activeUrl) {
        URL.revokeObjectURL(activeUrl)
      }
    }
  }, [recipe?.id])

  useEffect(() => {
    if (!id || id === '0') {
      return
    }

    const controller = new AbortController()
    let active = true
    let redirectTimer: ReturnType<typeof setTimeout> | undefined

    setProgress(0)
    setStage('esperando')
    setStatusMessage('Iniciando procesamiento...')
    setError('')

    const run = async () => {
      const base = (
        import.meta.env.VITE_API_BASE_URL || '/api'
      ).replace(/\/$/, '')

      const headers = new Headers({
        Accept: 'application/x-ndjson'
      })

      const token = getToken()

      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }

      let finished = false

      const handleLine = (line: string) => {
        if (!active || !line.trim()) {
          return
        }

        const event = JSON.parse(line) as ProcessingEvent

        if (event.stage === 'error') {
          throw new Error(event.message)
        }

        setStage(event.stage)
        setProgress(event.progress)
        setStatusMessage(event.message)

        if (event.recipe) {
          setRecipe(event.recipe)
        }

        if (event.stage === 'finalizado') {
          finished = true

          redirectTimer = setTimeout(() => {
            if (active) {
              navigate(`/validation/${id}`)
            }
          }, 1000)
        }
      }

      try {
        const response = await fetch(
          `${base}/processing/${id}/stream`,
          {
            method: 'POST',
            headers,
            signal: controller.signal
          }
        )

        if (!response.ok) {
          const body = await response.json().catch(() => null)

          throw new Error(
            typeof body?.detail === 'string'
              ? body.detail
              : 'No se pudo iniciar el procesamiento de la receta.'
          )
        }

        if (!response.body) {
          throw new Error(
            'No se pudo recibir el progreso del procesamiento.'
          )
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        try {
          while (true) {
            const { done, value } = await reader.read()

            if (done) {
              break
            }

            buffer += decoder.decode(value, { stream: true })

            let newline = buffer.indexOf('\n')

            while (newline !== -1) {
              const line = buffer.slice(0, newline)
              buffer = buffer.slice(newline + 1)
              handleLine(line)
              newline = buffer.indexOf('\n')
            }
          }

          buffer += decoder.decode()

          if (buffer.trim()) {
            handleLine(buffer)
          }

          if (!finished && active) {
            throw new Error(
              'Se interrumpió la comunicación antes de confirmar la finalización.'
            )
          }
        } finally {
          await reader.cancel().catch(() => {})
          reader.releaseLock()
        }
      } catch (err: unknown) {
        if (!active || controller.signal.aborted) {
          return
        }

        if (redirectTimer) {
          clearTimeout(redirectTimer)
        }

        setError(
          err instanceof Error
            ? err.message
            : 'No se pudo completar el procesamiento.'
        )
      }
    }

    // Permitir que React limpie el efecto antes de iniciar la petición.
    const startTimer = setTimeout(() => {
      void run()
    }, 0)

    return () => {
      active = false
      clearTimeout(startTimer)
      controller.abort()

      if (redirectTimer) {
        clearTimeout(redirectTimer)
      }
    }
  }, [id, navigate])

  if (!id || id === '0') {
    return (
      <div className="card processing-empty">
        <h1>Procesamiento</h1>
        <p>
          Primero carga una receta desde el módulo Subir Receta.
        </p>
        <Link className="primary-link" to="/upload">
          Subir receta
        </Link>
      </div>
    )
  }

  const currentIndex =
    stage === 'finalizado'
      ? stages.length
      : stages.findIndex(item => item.key === stage)

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <h1>Procesamiento de receta</h1>
          <p>
            Identificación automática de insumos y concentraciones
          </p>
        </div>
      </div>

      <section className="card">
        <div className="progress-title">
          <strong>
            {error
              ? 'Procesamiento detenido'
              : stage === 'finalizado'
                ? 'Procesamiento finalizado'
                : 'Procesamiento en curso...'}
          </strong>
          <span>{progress}%</span>
        </div>

        <div
          className="progress"
          role="progressbar"
          aria-label="Avance por etapas"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-valuetext={`${progress}%. ${statusMessage}`}
        >
          <div style={{ width: `${progress}%` }} />
        </div>

        <p role="status" aria-live="polite">
          {error
            ? 'El procesamiento no pudo completarse.'
            : statusMessage}
        </p>

        <small className="muted-text">
          Avance por etapas del procesamiento.
        </small>

        <ol>
          {stages.map((item, index) => {
            let label = 'Pendiente'

            if (index < currentIndex) {
              label = 'Completada'
            } else if (index === currentIndex) {
              label = error ? 'Interrumpida' : 'En curso'
            }

            return (
              <li key={item.key}>
                <strong>{item.label}</strong>: {label}
              </li>
            )
          })}
        </ol>

        {stage === 'finalizado' && !error && (
          <div className="success-box">
            Procesamiento finalizado. Redirigiendo a validación...
          </div>
        )}

        {error && (
          <div className="error-box" role="alert">
            {error}
          </div>
        )}
      </section>

      <div className="two-cols">
        <section className="card document-box">
          <h2>Receta Original</h2>

          {imageUrl ? (
            <img src={imageUrl} alt="Receta original" />
          ) : (
            <div className="doc-placeholder">
              <FileText size={45} />
            </div>
          )}
        </section>

        <section className="card extracted-box">
          <h2>Resultado del procesamiento</h2>

          <div className="extract-field active">
            <small>Estado</small>
            {error
              ? 'Procesamiento detenido.'
              : statusMessage}
          </div>

          <div className="extract-field">
            <small>Confianza del procesamiento</small>

            {stage === 'finalizado' &&
            recipe?.ocr_confidence != null
              ? `${recipe.ocr_confidence}%`
              : 'Pendiente...'}
          </div>
        </section>
      </div>
    </div>
  )
}