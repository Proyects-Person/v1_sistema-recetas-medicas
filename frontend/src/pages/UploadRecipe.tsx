import { CheckCircle2, FileText, ShieldCheck, UploadCloud, X } from 'lucide-react'
import { DragEvent, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Recipe } from '../types'

export default function UploadRecipe() {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string>('')
  const [patientName, setPatientName] = useState('')
  const [patientAge, setPatientAge] = useState('')
  const [patientPhone, setPatientPhone] = useState('')
  const [serviceReason, setServiceReason] = useState('analisis_receta')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const assignFile = (selected?: File) => {
    setError('')
    if (!selected) return
    if (!selected.type.startsWith('image/')) {
      setError('Archivo no válido. Solo se permiten imágenes PNG, JPG, JPEG o WEBP.')
      return
    }
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    assignFile(event.dataTransfer.files[0])
  }

  const upload = async () => {
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
      setError('La edad del paciente debe ser un número válido entre 0 y 130.')
      return
    }
    if (!/^\d{9}$/.test(patientPhone)) {
      setError('El teléfono del paciente es obligatorio y debe tener exactamente 9 dígitos.')
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
    setLoading(true)
    try {
      const recipe = await api.upload<Recipe>('/recipes/upload', form)
      navigate(`/processing/${recipe.id}`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-stack">
      <div className="page-title-row"><div><h1>Subir Receta</h1><p>Carga la imagen de la receta y registra los datos obligatorios del paciente</p></div></div>
      <div className="two-cols upload-cols">
        <section className="card upload-card">
          <h2>Cargar imagen</h2>
          <div className="dropzone" onDrop={onDrop} onDragOver={event => event.preventDefault()} onClick={() => inputRef.current?.click()}>
            {preview ? <img src={preview} className="preview-image" /> : <><UploadCloud size={42} /><strong>Arrastra y suelta o haz clic para subir</strong><span>PNG, JPG, JPEG o WEBP hasta 10MB</span></>}
          </div>
          <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/jpg,image/webp" hidden onChange={e => assignFile(e.target.files?.[0])} />
          {file && <div className="selected-file"><FileText size={17} /> {file.name}<button onClick={() => { setFile(null); setPreview('') }}><X size={15} /></button></div>}
          {error && <div className="error-box">{error}</div>}
          <button className="primary-btn" onClick={upload} disabled={loading}>{loading ? 'Cargando...' : 'Procesar receta'}</button>
        </section>
        <section className="card info-panel">
          <h2>Datos de evaluación</h2>
          <div className="form-stack compact-form">
            <label>Nombre del paciente *</label>
            <input required value={patientName} onChange={e => setPatientName(e.target.value)} placeholder="Ej. María González López" />
            <label>Edad *</label>
            <input required value={patientAge} onChange={e => setPatientAge(e.target.value.replace(/[^0-9]/g, ''))} inputMode="numeric" placeholder="Ej. 42" />
            <label>Teléfono de contacto del paciente *</label>
            <input required value={patientPhone} onChange={e => setPatientPhone(e.target.value.replace(/[^0-9]/g, '').slice(0, 9))} inputMode="numeric" maxLength={9} placeholder="Ej. 987654321" />
            <small className="muted-text">Debe contener exactamente 9 dígitos.</small>
            <label>Motivo de evaluación *</label>
            <select required value={serviceReason} onChange={e => setServiceReason(e.target.value)}>
              <option value="analisis_receta">Análisis de receta</option>
              <option value="preparacion_magistral">Preparar producto magistral</option>
              <option value="consulta_validacion">Consulta/validación farmacéutica</option>
              <option value="otro">Otro</option>
            </select>
          </div>
          <hr />
          <h2>Información del proceso</h2>
          <div className="process-step"><CheckCircle2 size={18} /><div><strong>OCR Cloud</strong><span>Transcripción real del texto visible en la receta</span></div></div>
          <div className="process-step"><CheckCircle2 size={18} /><div><strong>Diccionario farmacéutico</strong><span>Sugerencias para términos magistrales y abreviaturas frecuentes</span></div></div>
          <div className="process-step"><ShieldCheck size={18} /><div><strong>Validación farmacéutica</strong><span>Revisión, corrección y aprobación por químico farmacéutico</span></div></div>
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
