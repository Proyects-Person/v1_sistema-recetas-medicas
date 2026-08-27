const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export function getToken(): string | null {
  return localStorage.getItem('token')
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('token', token)
  else localStorage.removeItem('token')
}

function authHeaders(extra?: HeadersInit): Headers {
  const token = getToken()
  const headers = new Headers(extra || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return headers
}

async function parseError(response: Response): Promise<string> {
  let message = 'No se pudo completar la operación.'
  try {
    const error = await response.json()
    message = error.detail || message
  } catch (_) {}
  return message
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = authHeaders(options.headers)
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  if (response.status === 204) return undefined as T
  return response.json()
}

export async function fetchBlobUrl(path: string): Promise<string> {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

function filenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const match = disposition.match(/filename\*?=(?:UTF-8''|\")?([^";]+)/i)
  return match ? decodeURIComponent(match[1].replace(/"/g, '')) : fallback
}

export async function downloadFile(path: string, fallbackFilename: string) {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filenameFromDisposition(response.headers.get('Content-Disposition'), fallbackFilename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, data: FormData) => request<T>(path, { method: 'POST', body: data })
}

export const fileUrl = (path: string) => `${API_BASE}${path}`
