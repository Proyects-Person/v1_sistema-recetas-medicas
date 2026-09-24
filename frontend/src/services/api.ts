const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  '/api'


// ============================================================
// ERROR PERSONALIZADO DE LA API
// ============================================================

export class ApiError extends Error {

  status: number

  constructor(
    message: string,
    status: number
  ) {

    super(message)

    this.name = 'ApiError'

    this.status = status
  }
}


// ============================================================
// TOKEN
// ============================================================

export function getToken():
  string | null {

  return localStorage.getItem(
    'token'
  )
}


export function setToken(
  token: string | null
) {

  if (token) {

    localStorage.setItem(
      'token',
      token
    )

  } else {

    localStorage.removeItem(
      'token'
    )
  }
}


// ============================================================
// HEADERS DE AUTENTICACIÓN
// ============================================================

function authHeaders(
  extra?: HeadersInit
): Headers {

  const token =
    getToken()

  const headers =
    new Headers(
      extra || {}
    )

  if (token) {

    headers.set(
      'Authorization',
      `Bearer ${token}`
    )
  }

  return headers
}


// ============================================================
// VALIDACIÓN DE TELÉFONO
// ============================================================

function validatePhoneValue(
  value: unknown,
  fieldName: string
) {

  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {

    return
  }


  const phone =
    String(value).trim()


  if (
    !/^9\d{8}$/.test(phone)
  ) {

    throw new ApiError(
      `${fieldName} debe tener 9 dígitos y comenzar con 9.`,
      400
    )
  }
}


// ============================================================
// VALIDAR TELÉFONOS DE UN OBJETO
// ============================================================

function validateObjectPhones(
  value: unknown
) {

  if (
    value === null ||
    value === undefined
  ) {

    return
  }


  if (
    Array.isArray(value)
  ) {

    value.forEach(
      item =>
        validateObjectPhones(item)
    )

    return
  }


  if (
    typeof value !== 'object'
  ) {

    return
  }


  Object.entries(
    value as Record<string, unknown>
  ).forEach(
    ([key, currentValue]) => {

      if (
        key === 'phone'
      ) {

        validatePhoneValue(
          currentValue,
          'El teléfono'
        )

        return
      }


      if (
        key === 'patient_phone'
      ) {

        validatePhoneValue(
          currentValue,
          'El teléfono del paciente'
        )

        return
      }


      validateObjectPhones(
        currentValue
      )
    }
  )
}


// ============================================================
// VALIDAR TELÉFONOS EN FORMDATA
// ============================================================

function validateFormDataPhones(
  data: FormData
) {

  const userPhone =
    data.get('phone')

  if (
    typeof userPhone === 'string'
  ) {

    validatePhoneValue(
      userPhone,
      'El teléfono'
    )
  }


  const patientPhone =
    data.get('patient_phone')

  if (
    typeof patientPhone === 'string'
  ) {

    validatePhoneValue(
      patientPhone,
      'El teléfono del paciente'
    )
  }
}


// ============================================================
// VALIDACIÓN GENERAL ANTES DE ENVIAR
// ============================================================

function validateRequestData(
  body: unknown
) {

  if (!body) {

    return
  }


  if (
    body instanceof FormData
  ) {

    validateFormDataPhones(
      body
    )

    return
  }


  validateObjectPhones(
    body
  )
}


// ============================================================
// INTERPRETAR ERRORES DEL BACKEND
// ============================================================

async function parseError(
  response: Response
): Promise<string> {

  const fallback =
    'No se pudo completar la operación.'


  try {

    const error =
      await response.json()


    const detail =
      error?.detail


    // --------------------------------------------------------
    // FastAPI devuelve detail como texto
    // --------------------------------------------------------

    if (
      typeof detail === 'string'
    ) {

      return detail
    }


    // --------------------------------------------------------
    // FastAPI / Pydantic devuelve lista de validaciones
    // --------------------------------------------------------

    if (
      Array.isArray(detail)
    ) {

      const messages =
        detail
          .map(item => {

            if (
              typeof item === 'string'
            ) {

              return item
            }


            if (
              item &&
              typeof item.msg === 'string'
            ) {

              return item.msg
                .replace(
                  'Value error, ',
                  ''
                )
            }


            return null
          })
          .filter(Boolean)


      if (
        messages.length > 0
      ) {

        return messages.join(' ')
      }
    }


    // --------------------------------------------------------
    // Detail como objeto
    // --------------------------------------------------------

    if (
      detail &&
      typeof detail === 'object'
    ) {

      if (
        typeof detail.message
        === 'string'
      ) {

        return detail.message
      }


      if (
        typeof detail.msg
        === 'string'
      ) {

        return detail.msg
      }
    }


    // --------------------------------------------------------
    // Error genérico con message
    // --------------------------------------------------------

    if (
      typeof error?.message
      === 'string'
    ) {

      return error.message
    }

  } catch (_) {

    // Si el backend no devolvió JSON,
    // utilizamos el mensaje genérico.
  }


  return fallback
}


// ============================================================
// PETICIÓN GENERAL
// ============================================================

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {

  const headers =
    authHeaders(
      options.headers
    )


  if (
    !(options.body instanceof FormData)
  ) {

    headers.set(
      'Content-Type',
      'application/json'
    )
  }


  const response =
    await fetch(
      `${API_BASE}${path}`,
      {
        ...options,
        headers
      }
    )


  if (!response.ok) {

    throw new ApiError(
      await parseError(response),
      response.status
    )
  }


  if (
    response.status === 204
  ) {

    return undefined as T
  }


  return response.json()
}


// ============================================================
// OBTENER ARCHIVO COMO URL
// ============================================================

export async function fetchBlobUrl(
  path: string
): Promise<string> {

  const response =
    await fetch(
      `${API_BASE}${path}`,
      {
        headers:
          authHeaders()
      }
    )


  if (!response.ok) {

    throw new ApiError(
      await parseError(response),
      response.status
    )
  }


  const blob =
    await response.blob()


  return URL.createObjectURL(
    blob
  )
}


// ============================================================
// OBTENER NOMBRE DE ARCHIVO
// ============================================================

function filenameFromDisposition(
  disposition: string | null,
  fallback: string
): string {

  if (!disposition) {

    return fallback
  }


  const match =
    disposition.match(
      /filename\*?=(?:UTF-8''|\")?([^";]+)/i
    )


  return match
    ? decodeURIComponent(
        match[1].replace(
          /"/g,
          ''
        )
      )
    : fallback
}


// ============================================================
// DESCARGAR ARCHIVO
// ============================================================

export async function downloadFile(
  path: string,
  fallbackFilename: string
) {

  const response =
    await fetch(
      `${API_BASE}${path}`,
      {
        headers:
          authHeaders()
      }
    )


  if (!response.ok) {

    throw new ApiError(
      await parseError(response),
      response.status
    )
  }


  const blob =
    await response.blob()


  const url =
    URL.createObjectURL(
      blob
    )


  const link =
    document.createElement(
      'a'
    )


  link.href =
    url


  link.download =
    filenameFromDisposition(
      response.headers.get(
        'Content-Disposition'
      ),
      fallbackFilename
    )


  document.body.appendChild(
    link
  )


  link.click()


  link.remove()


  URL.revokeObjectURL(
    url
  )
}


// ============================================================
// MÉTODOS API
// ============================================================

export const api = {

  // ----------------------------------------------------------
  // GET
  // ----------------------------------------------------------

  get: <T>(
    path: string
  ) => {

    return request<T>(
      path
    )
  },


  // ----------------------------------------------------------
  // POST
  // ----------------------------------------------------------

  post: <T>(
    path: string,
    body?: unknown
  ) => {

    validateRequestData(
      body
    )


    return request<T>(
      path,
      {
        method: 'POST',

        body:
          body !== undefined
            ? JSON.stringify(body)
            : undefined
      }
    )
  },


  // ----------------------------------------------------------
  // PUT
  // ----------------------------------------------------------

  put: <T>(
    path: string,
    body?: unknown
  ) => {

    validateRequestData(
      body
    )


    return request<T>(
      path,
      {
        method: 'PUT',

        body:
          body !== undefined
            ? JSON.stringify(body)
            : undefined
      }
    )
  },


  // ----------------------------------------------------------
  // DELETE
  // ----------------------------------------------------------

  delete: <T>(
    path: string
  ) => {

    return request<T>(
      path,
      {
        method: 'DELETE'
      }
    )
  },


  // ----------------------------------------------------------
  // UPLOAD / FORMDATA
  // ----------------------------------------------------------

  upload: <T>(
    path: string,
    data: FormData
  ) => {

    validateRequestData(
      data
    )


    return request<T>(
      path,
      {
        method: 'POST',
        body: data
      }
    )
  }
}


// ============================================================
// URL DE ARCHIVOS
// ============================================================

export const fileUrl = (
  path: string
) =>
  `${API_BASE}${path}`