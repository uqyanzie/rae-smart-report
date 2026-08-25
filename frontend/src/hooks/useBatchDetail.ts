import { useEffect, useReducer } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

type Variant = components['schemas']['VariantPerformanceDTO']
type Product = components['schemas']['ProductSummaryDTO']

export interface BatchDetailData {
  variants: Variant[]
  products: Product[]
  crossVariants: Variant[]
  crossProducts: Product[]
}

export interface UseBatchDetailState {
  data: BatchDetailData | null
  loading: boolean
  error: string | null
}

type Action =
  | { type: 'start' }
  | { type: 'success'; data: BatchDetailData }
  | { type: 'failure'; message: string }

function reducer(_state: UseBatchDetailState, action: Action): UseBatchDetailState {
  switch (action.type) {
    case 'start':
      return { data: null, loading: true, error: null }
    case 'success':
      return { data: action.data, loading: false, error: null }
    case 'failure':
      return { data: null, loading: false, error: action.message }
  }
}

export function useBatchDetail(batchId: string): UseBatchDetailState {
  const [state, dispatch] = useReducer(reducer, { data: null, loading: true, error: null })

  useEffect(() => {
    let cancelled = false
    dispatch({ type: 'start' })
    Promise.all([
      apiClient.batchVariants(batchId, 0),
      apiClient.batchProducts(batchId, 0),
      apiClient.batchVariants(batchId, 1),
      apiClient.batchProducts(batchId, 1),
    ])
      .then(([variants, products, crossVariants, crossProducts]) => {
        if (!cancelled) {
          dispatch({ type: 'success', data: { variants, products, crossVariants, crossProducts } })
        }
      })
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? `${err.code}: ${err.message}` : String(err)
        if (!cancelled) dispatch({ type: 'failure', message })
      })
    return () => {
      cancelled = true
    }
  }, [batchId])

  return state
}
