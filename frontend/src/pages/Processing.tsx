import { FileText } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, fetchBlobUrl } from '../services/api'
import type { Recipe } from '../types'

export default function Processing() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [progress, setProgress] = useState(0)
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [imageUrl, setImageUrl] = useState('')
  const [error, setError] = useState('')
  const processedRef = useRef(false)

  useEffect(() => {
    if (!id || id === '0') return
    api.get<Recipe>(`/recipes/${id}`).then(setRecipe).catch(err => setError(err.message))
  }, [id])

  useEffect(() => {
    let activeUrl = ''
    if (!recipe) return undefined
    fetchBlobUrl(`/recipes/${recipe.id}/file`)
      .then(url => {
        activeUrl = url
        setImageUrl(url)
      })
      .catch(() => setImageUrl(''))
    return () => {
      if (activeUrl) URL.revokeObjectURL(activeUrl)
    }
  }, [recipe?.id])

  useEffect(() => {
    if (!id || id === '0') return
    processedRef.current = false
    const timer = setInterval(async () => {
      setProgress(prev => {
        const next = Math.min(prev + 15, 95)
        if (!processedRef.current && next >= 60) {
          processedRef.current = true
          api.post<Recipe>(`/recipes/${id}/process`)
            .then(result => {
              setRecipe(result)
              setProgress(100)
              setTimeout(() => navigate(`/validation/${id}`), 700)
            })
            .catch(err => {
              setError(err.message)
              setProgress(0)
            })
        }
        return next
      })
    }, 600)
    return () => clearInterval(timer)
  }, [id, navigate])

  if (!id || id === '0') return <div className="card processing-empty"><h1>Procesamiento</h1><p>Primero carga una receta desde el módulo Subir Receta.</p><Link className="primary-link" to="/upload">Subir receta</Link></div>

  return (
    <div className="page-stack">
      <div className="page-title-row"><div><h1>Procesamiento OCR</h1><p>Transcripción directa del contenido visible en la receta</p></div></div>
      <section className="card">
        <div className="progress-title"><strong>{error ? 'Procesamiento detenido' : 'Procesamiento OCR en curso...'}</strong><span>{progress}%</span></div>
        <div className="progress"><div style={{ width: `${progress}%` }} /></div>
        {progress === 100 && <div className="success-box">OCR finalizado. Redirigiendo a validación...</div>}
        {error && <div className="error-box">{error}</div>}
      </section>
      <div className="two-cols">
        <section className="card document-box"><h2>Receta Original</h2>{imageUrl ? <img src={imageUrl} /> : <div className="doc-placeholder"><FileText size={45} /></div>}</section>
        <section className="card extracted-box">
          <h2>Texto OCR detectado</h2>
          <div className="extract-field active"><small>Transcripción</small><pre>{recipe?.raw_text || 'Leyendo imagen con OCR real...'}</pre></div>
          <div className="extract-field"><small>Confianza OCR</small>{recipe?.ocr_confidence ? `${recipe.ocr_confidence}%` : 'Pendiente...'}</div>
        </section>
      </div>
    </div>
  )
}
