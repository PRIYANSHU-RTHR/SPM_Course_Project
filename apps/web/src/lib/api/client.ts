export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface ErrorBody {
  error?: { code?: string; message?: string; details?: Record<string, unknown> }
}

/** A failed request, carrying the backend's `{"error": {code, message, details}}` body. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(
    status: number,
    message: string,
    code = 'unknown_error',
    details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function readError(response: Response): Promise<ApiError> {
  const fallback = `Request failed with status ${response.status}`
  try {
    const body = (await response.json()) as ErrorBody
    return new ApiError(
      response.status,
      body.error?.message ?? fallback,
      body.error?.code,
      body.error?.details,
    )
  } catch {
    return new ApiError(response.status, fallback)
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError(0, 'Could not reach the API. Check that it is running.', 'network_error')
  }
  if (!response.ok) throw await readError(response)
  return (await response.json()) as T
}
