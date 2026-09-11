import type { components } from './api'

export interface ApiErrorEnvelope {
  status: 'error'
  code: string
  message: string
  details?: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

const API_BASE = '/api'

type RequestBody = BodyInit | Record<string, unknown> | null | undefined

async function request<T>(path: string, body?: RequestBody, query?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) {
      search.set(key, String(value))
    }
  }
  const qs = search.toString()
  const url = `${API_BASE}${path}${qs ? `?${qs}` : ''}`

  let init: RequestInit
  if (body instanceof FormData) {
    init = { method: 'POST', body }
  } else if (body !== undefined && body !== null) {
    init = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  } else {
    init = { method: 'GET' }
  }

  const res = await fetch(url, init)
  if (!res.ok) {
    throw await toApiError(res)
  }
  return (await res.json()) as T
}

function envelopeFromText(status: number, text: string): ApiError {
  let envelope: ApiErrorEnvelope | null = null
  try {
    envelope = JSON.parse(text) as ApiErrorEnvelope
  } catch {
    // Non-JSON error body; fall through to the generic envelope.
  }
  return new ApiError(
    status,
    envelope?.code ?? 'HTTP_ERROR',
    envelope?.message ?? `HTTP ${status}`,
    envelope?.details,
  )
}

async function toApiError(res: Response): Promise<ApiError> {
  return envelopeFromText(res.status, await res.text())
}

export const apiClient = {
  uploadFile(file: File, onProgress?: (percent: number) => void): Promise<components['schemas']['IngestionResultDTO']> {
    return new Promise((resolve, reject) => {
      const form = new FormData()
      form.append('file', file)

      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${API_BASE}/ingest`)
      xhr.responseType = 'text'
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as components['schemas']['IngestionResultDTO'])
          } catch {
            reject(new ApiError(xhr.status, 'HTTP_ERROR', 'Malformed upload response'))
          }
          return
        }
        reject(envelopeFromText(xhr.status, xhr.responseText))
      }
      xhr.onerror = () => reject(new ApiError(0, 'NETWORK_ERROR', 'Network error during upload'))
      xhr.send(form)
    })
  },

  ingest(file: File): Promise<components['schemas']['IngestionResultDTO']> {
    const form = new FormData()
    form.append('file', file)
    return request('/ingest', form)
  },

  profile(payload: components['schemas']['ProfileRequestDTO']): Promise<components['schemas']['ProfilerResponseDTO']> {
    return request('/profile', payload)
  },

  transform(payload: components['schemas']['TransformAndSaveRequestDTO']): Promise<components['schemas']['TransformResponseDTO']> {
    return request('/transform', payload)
  },

  listBatches(): Promise<components['schemas']['BatchSummaryDTO'][]> {
    return request('/reports/batches')
  },

  batchVariants(
    batchId: string,
    isCrossBundling = 0,
    isBundling?: number | null,
  ): Promise<components['schemas']['VariantPerformanceDTO'][]> {
    return request(`/reports/batches/${encodeURIComponent(batchId)}/variants`, undefined, {
      is_cross_bundling: isCrossBundling,
      isBundling,
    })
  },

  batchProducts(
    batchId: string,
    isCrossBundling = 0,
    isBundling?: number | null,
  ): Promise<components['schemas']['ProductSummaryDTO'][]> {
    return request(`/reports/batches/${encodeURIComponent(batchId)}/products`, undefined, {
      is_cross_bundling: isCrossBundling,
      isBundling,
    })
  },

  batchUnreported(batchId: string): Promise<components['schemas']['UnreportedVariantDTO'][]> {
    return request(`/reports/batches/${encodeURIComponent(batchId)}/unreported`)
  },

  aggregate(params: {
    platform?: string
    periodStart?: string
    periodEnd?: string
    isCrossBundling?: number
  }): Promise<components['schemas']['AggregateRowDTO'][]> {
    return request('/reports/aggregate', undefined, params)
  },

  deleteBatch(batchId: string): Promise<components['schemas']['DeleteBatchResponseDTO']> {
    return fetch(`${API_BASE}/reports/batches/${encodeURIComponent(batchId)}`, { method: 'DELETE' }).then(async (res) => {
      if (!res.ok) throw await toApiError(res)
      return (await res.json()) as components['schemas']['DeleteBatchResponseDTO']
    })
  },

  async exportExcel(
    selections: Array<{ batchId: string; includeCaseColours: boolean }>,
  ): Promise<{ blob: Blob; filename: string }> {
    const search = new URLSearchParams()
    for (const selection of selections) {
      search.append('batchIds', selection.batchId)
      if (selection.includeCaseColours) search.append('caseColorBatchIds', selection.batchId)
    }
    const res = await fetch(`${API_BASE}/export/excel?${search.toString()}`)
    if (!res.ok) throw await toApiError(res)
    const filename = parseFilenameFromDisposition(res.headers.get('content-disposition')) ?? 'rae_smart_report.xlsx'
    return { blob: await res.blob(), filename }
  },
}

function parseFilenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) return null
  const match = /filename="?([^";]+)"?/.exec(disposition)
  return match ? match[1] : null
}
