import { useCallback, useEffect, useState } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

interface UseBatchesData {
  batches: components['schemas']['BatchSummaryDTO'][]
  loading: boolean
  error: string | null
}

export function useBatches(): UseBatchesData & { remove: (batchId: string) => Promise<void> } {
  const [state, setState] = useState<UseBatchesData>({ batches: [], loading: true, error: null })
  const [reloadKey, setReloadKey] = useState(0)

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
  }, [reloadKey])

  const remove = useCallback(async (batchId: string): Promise<void> => {
    await apiClient.deleteBatch(batchId)
    setReloadKey((key) => key + 1)
  }, [])

  return { ...state, remove }
}
