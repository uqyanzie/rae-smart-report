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

async function toApiError(res: Response): Promise<ApiError> {
  let envelope: ApiErrorEnvelope | null = null
  try {
    envelope = (await res.json()) as ApiErrorEnvelope
  } catch {
    // Non-JSON error body; fall through to the generic envelope.
  }
  return new ApiError(
    res.status,
    envelope?.code ?? 'HTTP_ERROR',
    envelope?.message ?? res.statusText,
    envelope?.details,
  )
}

export const apiClient = {
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

  batchVariants(batchId: string, isCrossBundling = 0): Promise<components['schemas']['VariantPerformanceDTO'][]> {
    return request(`/reports/batches/${encodeURIComponent(batchId)}/variants`, undefined, { is_cross_bundling: isCrossBundling })
  },

  batchProducts(batchId: string, isCrossBundling = 0): Promise<components['schemas']['ProductSummaryDTO'][]> {
    return request(`/reports/batches/${encodeURIComponent(batchId)}/products`, undefined, { is_cross_bundling: isCrossBundling })
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

  async exportExcel(batchIds: string[]): Promise<Blob> {
    const search = new URLSearchParams()
    for (const id of batchIds) search.append('batchIds', id)
    const res = await fetch(`${API_BASE}/export/excel?${search.toString()}`)
    if (!res.ok) throw await toApiError(res)
    return res.blob()
  },
}
