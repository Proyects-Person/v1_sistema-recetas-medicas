import type { IngredientExtraction } from '../types'

interface Props {
  items: IngredientExtraction[]
}

export default function IngredientTable({ items }: Props) {
  return (
    <section className="ingredient-section">
      <div className="ingredient-section-header">
        <div>
          <h2>Receta estructurada</h2>
          <p className="muted-text">
            Solo se muestran los insumos y sus concentraciones con evidencia suficiente.
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="ingredient-empty">
          No se detectaron insumos con suficiente evidencia. Revisa el texto OCR y la receta original.
        </div>
      ) : (
        <div className="table-wrap">
          <table className="ingredient-table">
            <thead>
              <tr>
                <th>Insumo</th>
                <th>Concentración</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={`${item.ingredient}-${item.concentration || ''}-${index}`}>
                  <td>{item.ingredient}</td>
                  <td>{item.concentration || 'No identificada'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
