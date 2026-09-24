import {
  Plus,
  Trash2
} from 'lucide-react'

import type {
  IngredientExtraction
} from '../types'


interface Props {
  items: IngredientExtraction[]

  editable?: boolean

  onChange?: (
    items: IngredientExtraction[]
  ) => void
}


export default function IngredientTable({
  items,
  editable = false,
  onChange
}: Props) {

  const updateItem = (
    index: number,
    field: 'ingredient' | 'concentration',
    value: string
  ) => {

    if (!editable || !onChange) {
      return
    }

    const updated =
      items.map(
        (item, currentIndex) => {

          if (
            currentIndex !== index
          ) {
            return item
          }

          const sources =
            item.sources?.includes(
              'manual'
            )
              ? item.sources
              : [
                  ...(item.sources || []),
                  'manual'
                ]

          return {
            ...item,

            [field]:
              value,

            sources
          }
        }
      )

    onChange(
      updated
    )
  }


  const addItem = () => {

    if (!editable || !onChange) {
      return
    }

    onChange(
      [
        ...items,

        {
          ingredient: '',
          concentration: '',
          confidence: null,
          sources: [
            'manual'
          ],
          source_line: null,
          line_number:
            items.length + 1
        }
      ]
    )
  }


  const removeItem = (
    index: number
  ) => {

    if (!editable || !onChange) {
      return
    }

    onChange(
      items.filter(
        (_, currentIndex) =>
          currentIndex !== index
      )
    )
  }


  return (

    <section
      className="ingredient-section"
    >

      <div
        className="ingredient-section-header"
      >

        <div>

          <h2>
            Receta estructurada
          </h2>

          <p
            className="muted-text"
          >

            {editable
              ? (
                  'Revisa y corrige los insumos y concentraciones antes de validar la receta.'
                )
              : (
                  'Insumos y concentraciones registrados en la validación.'
                )
            }

          </p>

        </div>


        {editable && (

          <button
            type="button"
            className="outline-btn"
            onClick={addItem}
          >

            <Plus size={16} />

            Agregar insumo

          </button>

        )}

      </div>


      {items.length === 0 ? (

        <div
          className="ingredient-empty"
        >

          No se registraron insumos
          estructurados para esta receta.

          {editable && (
            <>
              {' '}
              Puedes agregarlos manualmente.
            </>
          )}

        </div>

      ) : (

        <div
          className="table-wrap"
        >

          <table
            className="ingredient-table"
          >

            <thead>

              <tr>

                <th>
                  Insumo
                </th>

                <th>
                  Concentración
                </th>

                {editable && (
                  <th>
                    Acción
                  </th>
                )}

              </tr>

            </thead>


            <tbody>

              {items.map(
                (item, index) => (

                  <tr
                    key={`ingredient-${index}`}
                  >

                    <td>

                      {editable ? (

                        <input
                          value={
                            item.ingredient
                          }
                          onChange={
                            event =>
                              updateItem(
                                index,
                                'ingredient',
                                event.target.value
                              )
                          }
                          placeholder="Ej. Adapaleno"
                        />

                      ) : (

                        item.ingredient

                      )}

                    </td>


                    <td>

                      {editable ? (

                        <input
                          value={
                            item.concentration
                            || ''
                          }
                          onChange={
                            event =>
                              updateItem(
                                index,
                                'concentration',
                                event.target.value
                              )
                          }
                          placeholder="Ej. 0.1%"
                        />

                      ) : (

                        item.concentration
                        || 'No identificada'

                      )}

                    </td>


                    {editable && (

                      <td>

                        <button
                          type="button"
                          className="icon-link danger-icon"
                          title="Eliminar insumo"
                          onClick={
                            () =>
                              removeItem(
                                index
                              )
                          }
                        >

                          <Trash2
                            size={17}
                          />

                        </button>

                      </td>

                    )}

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      )}

    </section>

  )
}