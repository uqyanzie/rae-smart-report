import { useEffect, useState } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

interface UseBatchesState {
  batches: components['schemas']['BatchSummaryDTO'][]
  loading: boolean
  error: string | null
}

export function useBatches(): UseBatchesState {
  const [state, setState] = useState<UseBatchesState>({ batches: [], loading: true, error: null })

  useEffect(() => {
    let cancelled = false
    apiClient
      .listBatches()
      .then((batches) => {
        if (!cancelled) setState({ batches, loading: false, error: null })
      })
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? `${err.code}: ${err.message}` : String(err)
        if (!cancelled) setState({ batches: [], loading: false, error: message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
