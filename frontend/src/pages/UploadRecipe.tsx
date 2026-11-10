import {
  CheckCircle2,
  FileText,
  ShieldCheck,
  UploadCloud,
  X
} from 'lucide-react'
import { DragEvent, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Recipe } from '../types'

const INVALID_IMAGE_MESSAGE =
  'No se puede adjuntar el archivo porque está dañado ' +
  'o no corresponde a una imagen válida. Selecciona otra imagen.'

const INVALID_FORMAT_MESSAGE =
  'Archivo no válido. Solo se permiten imágenes PNG, JPG, JPEG o WEBP.'

const ALLOWED_EXTENSIONS = new Set([
  'png',
  'jpg',
  'jpeg',
  'webp'
])

const MAX_FILE_SIZE = 10 * 1024 * 1024

type ImageValidationResult = {
  valid: boolean
  format: string
  width: number
  height: number
}

export default function UploadRecipe() {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const previewRef = useRef('')
  const selectionRef = useRef(0)
  const validatingRef = useRef(false)
  const uploadingRef = useRef(false)

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [patientName, setPatientName] = useState('')
  const [patientAge, setPatientAge] = useState('')
  const [patientPhone, setPatientPhone] = useState('')
  const [serviceReason, setServiceReason] = useState(
    'analisis_receta'
  )
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)

  const navigate = useNavigate()

  useEffect(() => {
    return () => {
      // Ignorar respuestas pendientes cuando se abandona la pantalla.
      selectionRef.current += 1

      if (previewRef.current) {
        URL.revokeObjectURL(previewRef.current)
        previewRef.current = ''
      }
    }
  }, [])

  const clearSelectedFile = () => {
    setFile(null)
    setPreview('')

    if (previewRef.current) {
      URL.revokeObjectURL(previewRef.current)
      previewRef.current = ''
    }

    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  const removeFile = () => {
    if (uploadingRef.current) {
      return
    }

    selectionRef.current += 1
    validatingRef.current = false
    setValidating(false)
    setError('')
    clearSelectedFile()
  }

  const assignFile = async (selected?: File) => {
    if (!selected || uploadingRef.current) {
      return
    }

    const selection = ++selectionRef.current

    setError('')
    clearSelectedFile()
    validatingRef.current = false
    setValidating(false)

    const extension = selected.name
      .split('.')
      .pop()
      ?.toLowerCase()

    if (!extension || !ALLOWED_EXTENSIONS.has(extension)) {
      setError(INVALID_FORMAT_MESSAGE)
      return
    }

    if (selected.size === 0) {
      setError(INVALID_IMAGE_MESSAGE)
      return
    }

    if (selected.size > MAX_FILE_SIZE) {
      setError('El archivo supera el límite permitido de 10MB.')
      return
    }

    validatingRef.current = true
    setValidating(true)

    try {
      const validationForm = new FormData()
      validationForm.append('file', selected)

      // El backend abre y decodifica la imagen.
      // No guarda el archivo ni crea una receta en esta ruta.
      const result = await api.upload<ImageValidationResult>(
        '/images/validate',
        validationForm
      )

      // Si el usuario eligió otro archivo, ignorar esta respuesta.
      if (selection !== selectionRef.current) {
        return
      }

      if (!result.valid) {
        throw new Error(INVALID_IMAGE_MESSAGE)
      }

      // Aceptar el adjunto únicamente después de validarlo.
      const url = URL.createObjectURL(selected)

      previewRef.current = url
      setPreview(url)
      setFile(selected)
    } catch (err: unknown) {
      if (selection !== selectionRef.current) {
        return
      }

      clearSelectedFile()

      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo validar el archivo. Inténtalo nuevamente.'
      )
    } finally {
      if (selection === selectionRef.current) {
        validatingRef.current = false
        setValidating(false)
      }
    }
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()

    if (uploadingRef.current) {
      return
    }

    void assignFile(event.dataTransfer.files[0])
  }

  const upload = async () => {
    if (uploadingRef.current) {
      return
    }

    if (validatingRef.current) {
      setError('Espera a que termine la validación del archivo.')
      return
    }

    setError('')

    if (!patientName.trim()) {
      setError('El nombre del paciente es obligatorio.')
      return
    }

    if (!patientAge.trim()) {
      setError('La edad del paciente es obligatoria.')
      return
    }

    const age = Number(patientAge)

    if (!Number.isInteger(age) || age < 0 || age > 130) {
      setError(
        'La edad del paciente debe ser un número válido entre 0 y 130.'
      )
      return
    }

    if (!/^\d{9}$/.test(patientPhone)) {
      setError(
        'El teléfono del paciente es obligatorio y debe tener exactamente 9 dígitos.'
      )
      return
    }

    if (!file) {
      setError('Debe cargar una receta antes de procesar.')
      return
    }

    const form = new FormData()

    form.append('file', file)
    form.append('patient_name', patientName.trim())
    form.append('patient_age', patientAge.trim())
    form.append('patient_phone', patientPhone.trim())
    form.append('service_reason', serviceReason)

    uploadingRef.current = true
    setLoading(true)

    try {
      const recipe = await api.upload<Recipe>(
        '/recipes/upload',
        form
      )

      navigate(`/processing/${recipe.id}`)
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo cargar la receta. Inténtalo nuevamente.'
      )
    } finally {
      uploadingRef.current = false
      setLoading(false)
    }
  }

  return (
    <div className="page-stack">
      <div className="page-title-row">
        <div>
          <h1>Subir Receta</h1>
          <p>
            Carga la imagen de la receta y registra los datos
            obligatorios del paciente
          </p>
        </div>
      </div>

      <div className="two-cols upload-cols">
        <section className="card upload-card">
          <h2>Cargar imagen</h2>

          <div
            className="dropzone"
            onDrop={onDrop}
            onDragOver={event => event.preventDefault()}
            onClick={() => {
              if (!uploadingRef.current) {
                inputRef.current?.click()
              }
            }}
            aria-busy={validating}
          >
            {validating ? (
              <>
                <UploadCloud size={42} />
                <strong role="status">
                  Validando imagen...
                </strong>
                <span>
                  Comprobando que el archivo pueda leerse correctamente
                </span>
              </>
            ) : preview ? (
              <img
                src={preview}
                className="preview-image"
                alt="Vista previa de la receta seleccionada"
              />
            ) : (
              <>
                <UploadCloud size={42} />
                <strong>
                  Arrastra y suelta o haz clic para subir
                </strong>
                <span>
                  PNG, JPG, JPEG o WEBP hasta 10MB
                </span>
              </>
            )}
          </div>

          <input
            ref={inputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.webp"
            hidden
            disabled={loading}
            onChange={event => {
              void assignFile(event.target.files?.[0])
            }}
          />

          {file && (
            <div className="selected-file">
              <FileText size={17} />
              {file.name}

              <button
                type="button"
                onClick={removeFile}
                disabled={loading}
                title="Retirar archivo"
                aria-label="Retirar archivo"
              >
                <X size={15} />
              </button>
            </div>
          )}

          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}

          <button
            type="button"
            className="primary-btn"
            onClick={upload}
            disabled={loading || validating}
          >
            {loading
              ? 'Cargando...'
              : validating
                ? 'Validando imagen...'
                : 'Procesar receta'}
          </button>
        </section>

        <section className="card info-panel">
          <h2>Datos de evaluación</h2>

          <div className="form-stack compact-form">
            <label>Nombre del paciente *</label>
            <input
              required
              value={patientName}
              onChange={event =>
                setPatientName(event.target.value)
              }
              placeholder="Ej. María González López"
            />

            <label>Edad *</label>
            <input
              required
              value={patientAge}
              onChange={event =>
                setPatientAge(
                  event.target.value.replace(/[^0-9]/g, '')
                )
              }
              inputMode="numeric"
              placeholder="Ej. 42"
            />

            <label>Teléfono de contacto del paciente *</label>
            <input
              required
              value={patientPhone}
              onChange={event =>
                setPatientPhone(
                  event.target.value
                    .replace(/[^0-9]/g, '')
                    .slice(0, 9)
                )
              }
              inputMode="numeric"
              maxLength={9}
              placeholder="Ej. 987654321"
            />

            <small className="muted-text">
              Debe contener exactamente 9 dígitos.
            </small>

            <label>Motivo de evaluación *</label>
            <select
              required
              value={serviceReason}
              onChange={event =>
                setServiceReason(event.target.value)
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

          <hr />

          <h2>Información del proceso</h2>

          <strong>Procesamiento OCR</strong>
          <span>
            Extracción automática de información para identificar
            insumos y concentraciones
          </span>

          <div className="process-step">
            <CheckCircle2 size={18} />
            <div>
              <strong>Diccionario farmacéutico</strong>
              <span>
                Sugerencias para términos magistrales
                y abreviaturas frecuentes
              </span>
            </div>
          </div>

          <div className="process-step">
            <ShieldCheck size={18} />
            <div>
              <strong>Validación farmacéutica</strong>
              <span>
                Revisión, corrección y aprobación por
                químico farmacéutico
              </span>
            </div>
          </div>

          <h3>Recomendaciones</h3>
          <ul>
            <li>Imagen clara y bien iluminada</li>
            <li>Enfoque nítido del texto manuscrito</li>
            <li>Evitar recortes extremos de la fórmula</li>
            <li>Sin sombras ni reflejos</li>
          </ul>
        </section>
      </div>
    </div>
  )
}