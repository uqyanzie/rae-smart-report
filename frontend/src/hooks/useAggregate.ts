import { useEffect, useReducer } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

type AggregateRow = components['schemas']['AggregateRowDTO']

interface AggregateState {
  rows: AggregateRow[]
  loading: boolean
  error: string | null
}

type Action =
  | { type: 'start' }
  | { type: 'success'; rows: AggregateRow[] }
  | { type: 'failure'; message: string }

function reducer(_state: AggregateState, action: Action): AggregateState {
  switch (action.type) {
    case 'start':
      return { rows: [], loading: true, error: null }
    case 'success':
      return { rows: action.rows, loading: false, error: null }
    case 'failure':
      return { rows: [], loading: false, error: action.message }
  }
}

export function useAggregate(
  platform?: string,
  periodStart?: string,
  periodEnd?: string,
  isCrossBundling?: number,
): AggregateState {
  const [state, dispatch] = useReducer(reducer, { rows: [], loading: true, error: null })

  useEffect(() => {
    let cancelled = false
    dispatch({ type: 'start' })
    apiClient
      .aggregate({ platform, periodStart, periodEnd, isCrossBundling })
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
  }, [platform, periodStart, periodEnd, isCrossBundling])

  return state
}
