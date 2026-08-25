import { useEffect, useMemo, useReducer } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

type Variant = components['schemas']['VariantPerformanceDTO']

export type DashboardFilterType = 'single' | 'bundling' | 'cross'

export interface DashboardVariant extends Variant {
  source: DashboardFilterType
}

export interface GroupRollup {
  productGroup: string
  totalQty: number
  totalRevenue: number
  share: number
}

interface DashboardDatasets {
  single: Variant[]
  bundling: Variant[]
  cross: Variant[]
}

interface UseBatchDashboardState {
  datasets: DashboardDatasets | null
  loading: boolean
  error: string | null
}

type Action =
  | { type: 'start' }
  | { type: 'success'; datasets: DashboardDatasets }
  | { type: 'failure'; message: string }

function reducer(_state: UseBatchDashboardState, action: Action): UseBatchDashboardState {
  switch (action.type) {
    case 'start':
      return { datasets: null, loading: true, error: null }
    case 'success':
      return { datasets: action.datasets, loading: false, error: null }
    case 'failure':
      return { datasets: null, loading: false, error: action.message }
  }
}

const SOURCE_ORDER: DashboardFilterType[] = ['single', 'bundling', 'cross']

export function useBatchDashboard(
  batchId: string,
  active: DashboardFilterType[],
): {
  variants: DashboardVariant[]
  rollups: GroupRollup[]
  totalQty: number
  totalRevenue: number
  loading: boolean
  error: string | null
} {
  const [state, dispatch] = useReducer(reducer, { datasets: null, loading: false, error: null })

  useEffect(() => {
    if (!batchId) return
    let cancelled = false
    dispatch({ type: 'start' })
    Promise.all([
      apiClient.batchVariants(batchId, 0, 0),
      apiClient.batchVariants(batchId, 0, 1),
      apiClient.batchVariants(batchId, 1),
    ])
      .then(([single, bundling, cross]) => {
        if (!cancelled) {
          dispatch({ type: 'success', datasets: { single, bundling, cross } })
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

  const activeKey = useMemo(() => [...active].sort().join(','), [active])

  const { variants, rollups, totalQty, totalRevenue } = useMemo(() => {
    if (!state.datasets) {
      return { variants: [], rollups: [], totalQty: 0, totalRevenue: 0 }
    }
    const activeSet = new Set(activeKey ? activeKey.split(',') : [])

    const selected: DashboardVariant[] = []
    for (const source of SOURCE_ORDER) {
      if (!activeSet.has(source)) continue
      for (const row of state.datasets[source]) {
        selected.push({ ...row, source })
      }
    }

    const byGroup = new Map<string, { qty: number; revenue: number }>()
    for (const row of selected) {
      const entry = byGroup.get(row.productGroup) ?? { qty: 0, revenue: 0 }
      entry.qty += row.totalQty
      entry.revenue += row.totalRevenue
      byGroup.set(row.productGroup, entry)
    }
    const groupTotal = Array.from(byGroup.values()).reduce((sum, entry) => sum + entry.qty, 0)
    const rollups: GroupRollup[] = Array.from(byGroup.entries())
      .map(([productGroup, entry]) => ({
        productGroup,
        totalQty: entry.qty,
        totalRevenue: entry.revenue,
        share: groupTotal > 0 ? entry.qty / groupTotal : 0,
      }))
      .sort((a, b) => b.totalQty - a.totalQty)

    const totalQty = selected.reduce((sum, row) => sum + row.totalQty, 0)
    const totalRevenue = selected.reduce((sum, row) => sum + row.totalRevenue, 0)
    return { variants: selected, rollups, totalQty, totalRevenue }
  }, [state.datasets, activeKey])

  return { variants, rollups, totalQty, totalRevenue, loading: state.loading, error: state.error }
}
