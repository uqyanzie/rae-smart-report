import { useEffect, useMemo, useReducer } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

type Unreported = components['schemas']['UnreportedVariantDTO']

export interface UnreportedTotals {
  rows: number
  qty: number
  revenue: number
}

interface UseUnreportedState {
  rows: Unreported[]
  loading: boolean
  error: string | null
}

type Action =
  | { type: 'start' }
  | { type: 'success'; rows: Unreported[] }
  | { type: 'failure'; message: string }

function reducer(_state: UseUnreportedState, action: Action): UseUnreportedState {
  switch (action.type) {
    case 'start':
      return { rows: [], loading: true, error: null }
    case 'success':
      return { rows: action.rows, loading: false, error: null }
    case 'failure':
      return { rows: [], loading: false, error: action.message }
  }
}

/**
 * Fetches the persisted non-reportable entries for a batch (Query G).
 *
 * These rows are stored for traceability but never appear in a report figure
 * or the Produk sheets; they are shown separately on the dashboard and batch
 * detail views.
 */
export function useUnreported(batchId: string): {
  rows: Unreported[]
  totals: UnreportedTotals
  loading: boolean
  error: string | null
} {
  const [state, dispatch] = useReducer(reducer, { rows: [], loading: false, error: null })

  useEffect(() => {
    if (!batchId) return
    let cancelled = false
    dispatch({ type: 'start' })
    apiClient
      .batchUnreported(batchId)
      .then((rows) => {
        if (!cancelled) dispatch({ type: 'success', rows })
      })
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? `${err.code}: ${err.message}` : String(err)
        if (!cancelled) dispatch({ type: 'failure', message })
      })
    return () => {
      cancelled = true
    }
  }, [batchId])

  const totals = useMemo<UnreportedTotals>(() => {
    return {
      rows: state.rows.length,
      qty: state.rows.reduce((sum, row) => sum + row.totalQty, 0),
      revenue: state.rows.reduce((sum, row) => sum + row.totalRevenue, 0),
    }
  }, [state.rows])

  return { rows: state.rows, totals, loading: state.loading, error: state.error }
}
