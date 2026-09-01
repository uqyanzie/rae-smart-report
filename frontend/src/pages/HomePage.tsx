import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from 'recharts'
import { useBatches } from '../hooks/useBatches'
import { useBatchDashboard, type DashboardFilterType } from '../hooks/useBatchDashboard'
import { useUnreported } from '../hooks/useUnreported'
import { formatCurrency, formatNumber, formatPercent } from '../utils/format'

const FILTER_OPTIONS: { key: DashboardFilterType; label: string }[] = [
  { key: 'single', label: 'Single Data' },
  { key: 'bundling', label: 'Bundling Data' },
  { key: 'cross', label: 'Cross Bundling Data' },
]

const SOURCE_LABELS: Record<DashboardFilterType, string> = {
  single: 'Single',
  bundling: 'Bundling',
  cross: 'Cross Bundling',
}

const COLORS = [
  '#ec4899',
  '#84cc16',
  '#14b8a6',
  '#f97316',
  '#3b82f6',
  '#a855f7',
  '#6366f1',
  '#8b5cf6',
  '#06b6d4',
  '#10b981',
  '#f59e0b',
  '#ef4444'
]

const PIE_HEIGHT = 560
const RADIAN = Math.PI / 180

// Dashboard chart display (DevelopmentFeedback20260826): pie slices below this
// share merge into "Other"; long product-group labels are truncated in chart
// tooltips unless the group is a major contributor or the user toggles
// "Show all labels".
const MIN_MAJOR_SHARE = 0.01
const MAX_LABEL_LENGTH = 84
const OTHER_COLOR = '#94a3b8'

interface PieSlice {
  name: string
  value: number
  share: number
  merged?: number
}

interface BarPoint {
  name: string
  revenue: number
  share: number
}

function formatTooltipLabel(name: string, share: number, showAll: boolean): string {
  if (showAll || share >= MIN_MAJOR_SHARE) return name
  return name.length > MAX_LABEL_LENGTH ? `${name.slice(0, MAX_LABEL_LENGTH)}…` : name
}

function renderPieLabel(props: {
  cx?: number
  cy?: number
  midAngle?: number
  innerRadius?: number
  outerRadius?: number
  percent?: number
}) {
  const { cx = 0, cy = 0, midAngle = 0, innerRadius = 0, outerRadius = 0, percent = 0 } = props
  if (percent < 0.03) return null
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5 + 26
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text
      x={x}
      y={y}
      fill="#000"
      fontWeight="bold"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={12}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

const thClass = 'px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500'
const tdClass = 'px-4 py-2 text-slate-700'

export default function HomePage() {
  const { batches, loading: batchesLoading, error: batchesError } = useBatches()
  const [batchId, setBatchId] = useState('')
  const [activeTypes, setActiveTypes] = useState<DashboardFilterType[]>([
    'single',
    'bundling',
    'cross',
  ])
  const [showAllLabels, setShowAllLabels] = useState(false)

  const selectedBatchId = batchId || batches[0]?.importBatchId || ''
  const { variants, rollups, totalQty, totalRevenue, loading, error } = useBatchDashboard(
    selectedBatchId,
    activeTypes,
  )
  const {
    rows: unreportedRows,
    totals: unreportedTotals,
    loading: unreportedLoading,
    error: unreportedError,
  } = useUnreported(selectedBatchId)

  const toggleType = (key: DashboardFilterType) => {
    setActiveTypes((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    )
  }

  // Pie slices: merge product groups contributing < 5% of the active subset
  // quantity into a single "Other" slice (DevelopmentFeedback20260826).
  const pieSlices = useMemo<PieSlice[]>(() => {
    const slices: PieSlice[] = []
    let minorValue = 0
    let minorCount = 0
    for (const row of rollups) {
      if (showAllLabels || row.share >= MIN_MAJOR_SHARE) {
        slices.push({ name: row.productGroup, value: row.totalQty, share: row.share })
      } else {
        minorValue += row.totalQty
        minorCount += 1
      }
    }
    // Order slices by highest contribution descending; the aggregated "Other"
    // bucket stays last so it reads as a catch-all tail.
    slices.sort((a, b) => b.share - a.share)
    if (minorCount > 0 && minorValue > 0) {
      slices.push({
        name: 'Other',
        value: minorValue,
        share: totalQty > 0 ? minorValue / totalQty : 0,
        merged: minorCount,
      })
    }
    return slices
  }, [rollups, totalQty, showAllLabels])

  const barData = rollups
    .map((row) => ({
      name: row.productGroup,
      revenue: row.totalRevenue,
      share: row.share,
    }))
    .sort((a, b) => b.share - a.share)
  const barHeight = Math.max(440, rollups.length * 38 + 60)

  const renderPieTooltip = ({ active, payload }: TooltipContentProps) => {
    if (!active || !payload || payload.length === 0) return null
    const point = payload[0]?.payload as PieSlice | undefined
    if (!point) return null
    return (
      <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
        <p className="font-semibold text-slate-800">
          {formatTooltipLabel(point.name, point.share, showAllLabels)}
        </p>
        <p className="mt-0.5 text-slate-600">{formatNumber(point.value)} units</p>
        {point.merged !== undefined && (
          <p className="text-slate-500">{point.merged} product groups merged</p>
        )}
        <p className="mt-0.5 text-slate-600">{formatPercent(point.share)}</p>
      </div>
    )
  }

  const renderBarTooltip = ({ active, payload }: TooltipContentProps) => {
    if (!active || !payload || payload.length === 0) return null
    const point = payload[0]?.payload as BarPoint | undefined
    if (!point) return null
    return (
      <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
        <p className="font-semibold text-slate-800">
          {formatTooltipLabel(point.name, point.share, showAllLabels)}
        </p>
        <p className="mt-0.5 text-slate-600">{formatCurrency(point.revenue)}</p>
        <p className="mt-0.5 text-slate-600">{formatPercent(point.share)} contribution</p>
      </div>
    )
  }

  return (
    <section className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Dashboard</h1>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-end gap-6">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
            Batch
            <select
              value={selectedBatchId}
              onChange={(event) => setBatchId(event.target.value)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {batches.map((batch) => (
                <option key={batch.importBatchId} value={batch.importBatchId}>
                  {batch.platform} — {batch.importBatchId}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="flex flex-col gap-1">
            <legend className="text-xs font-medium text-slate-600">Data types</legend>
            <div className="flex flex-wrap gap-4">
              {FILTER_OPTIONS.map((option) => (
                <label
                  key={option.key}
                  className="flex items-center gap-2 text-sm text-slate-700"
                >
                  <input
                    type="checkbox"
                    checked={activeTypes.includes(option.key)}
                    onChange={() => toggleType(option.key)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </div>

      {batchesLoading && <p className="text-sm text-slate-500">Loading batches…</p>}
      {batchesError && <p className="text-sm text-red-600">{batchesError}</p>}
      {!batchesLoading && !batchesError && batches.length === 0 && (
        <p className="text-sm text-slate-500">No batches yet — upload a spreadsheet to begin.</p>
      )}

      {selectedBatchId && batches.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Variant rows</p>
              <p className="mt-1 text-lg font-semibold text-slate-800">
                {formatNumber(variants.length)}
              </p>
            </div>
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
              <p className="text-xs font-medium text-indigo-600">Total units</p>
              <p className="mt-1 text-lg font-semibold text-indigo-800">
                {formatNumber(totalQty)}
              </p>
            </div>
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
              <p className="text-xs font-medium text-indigo-600">Total revenue</p>
              <p className="mt-1 text-lg font-semibold text-indigo-800">
                {formatCurrency(totalRevenue)}
              </p>
            </div>
            <div className="rounded-lg border border-stone-400 bg-amber-50 p-4">
              <p className="text-xs font-medium text-slate-500">Unreported revenue</p>
              <p className="mt-1 text-lg font-semibold text-slate-800">
                {formatCurrency(unreportedTotals.revenue)}
              </p>
            </div>
          </div>

          {loading && <p className="text-sm text-slate-500">Loading batch data…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          {!loading && !error && rollups.length === 0 && (
            <p className="text-sm text-slate-500">
              {activeTypes.length === 0
                ? 'Select at least one data type.'
                : 'No data for the selected filters.'}
            </p>
          )}

          {!loading && !error && rollups.length > 0 && (
            <div className="space-y-6">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-sm font-semibold text-slate-700">
                    Contribution (units per product group)
                  </h2>
                  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
                    <input
                      type="checkbox"
                      checked={showAllLabels}
                      onChange={(event) => setShowAllLabels(event.target.checked)}
                      className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    Show all labels
                  </label>
                </div>
                <ResponsiveContainer width="100%" height={PIE_HEIGHT}>
                  <PieChart>
                    <Pie
                      data={pieSlices}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="46%"
                      outerRadius="70%"
                      labelLine={{ stroke: '#94a3b8' }}
                      label={renderPieLabel}
                    >
                      {pieSlices.map((entry, index) => (
                        <Cell
                          key={entry.name}
                          fill={entry.name === 'Other' ? OTHER_COLOR : COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip content={renderPieTooltip} />
                    <Legend
                      verticalAlign="bottom"
                      height={40}
                      wrapperStyle={{ fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="mb-2 text-sm font-semibold text-slate-700">
                  Product sales (revenue per product group)
                </h2>
                <ResponsiveContainer width="100%" height={barHeight}>
                  <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickFormatter={(value) => formatNumber(Number(value))} />
                    <YAxis type="category" dataKey="name" width={220} tick={{ fontSize: 11 }} />
                    <Tooltip content={renderBarTooltip} />
                    <Bar dataKey="revenue" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {!loading && !error && variants.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className={thClass}>Product group</th>
                      <th className={thClass}>Variant</th>
                      <th className={thClass}>Type</th>
                      <th className={`${thClass} text-right`}>Qty</th>
                      <th className={`${thClass} text-right`}>Revenue</th>
                      <th className={`${thClass} text-right`}>Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {variants.map((row) => {
                      const share = totalQty > 0 ? row.totalQty / totalQty : 0
                      return (
                        <tr
                          key={`${row.source}-${row.productGroup}-${row.cleanVariant}`}
                          className="hover:bg-slate-50"
                        >
                          <td className={`${tdClass} font-medium text-slate-800`}>
                            {row.productGroup}
                          </td>
                          <td className={tdClass}>{row.cleanVariant}</td>
                          <td className={tdClass}>
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                              {SOURCE_LABELS[row.source]}
                            </span>
                          </td>
                          <td className={`${tdClass} text-right`}>{formatNumber(row.totalQty)}</td>
                          <td className={`${tdClass} text-right`}>
                            {formatCurrency(row.totalRevenue)}
                          </td>
                          <td className={`${tdClass} text-right`}>{formatPercent(share)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot className="bg-slate-50">
                    <tr>
                      <td colSpan={2} className="px-4 py-2 text-xs font-medium text-slate-500">
                        Selected totals
                      </td>
                      <td className="px-4 py-2 text-xs font-medium text-slate-500">
                        {variants.length} rows
                      </td>
                      <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">
                        {formatNumber(totalQty)}
                      </td>
                      <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">
                        {formatCurrency(totalRevenue)}
                      </td>
                      <td className="px-4 py-2" />
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}

          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">Unreported entries</h2>
                <p className="text-xs text-slate-500">
                  Persisted but not reported — off-grid variants and non-catalog products
                </p>
              </div>
              <div className="flex flex-wrap gap-4 text-xs text-slate-600">
                <span>
                  <span className="font-semibold text-slate-800">{formatNumber(unreportedTotals.rows)}</span>{' '}
                  rows
                </span>
                <span>
                  <span className="font-semibold text-slate-800">{formatNumber(unreportedTotals.qty)}</span>{' '}
                  units
                </span>
                <span>
                  <span className="font-semibold text-slate-800">
                    {formatCurrency(unreportedTotals.revenue)}
                  </span>{' '}
                  revenue
                </span>
              </div>
            </div>

            {unreportedLoading && <p className="px-4 py-3 text-sm text-slate-500">Loading unreported entries…</p>}
            {unreportedError && <p className="px-4 py-3 text-sm text-red-600">{unreportedError}</p>}
            {!unreportedLoading && !unreportedError && unreportedRows.length === 0 && (
              <p className="px-4 py-3 text-sm text-slate-500">
                No unreported entries for this batch.
              </p>
            )}
            {!unreportedLoading && !unreportedError && unreportedRows.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className={thClass}>Product group</th>
                      <th className={thClass}>Variant</th>
                      <th className={thClass}>Raw product</th>
                      <th className={thClass}>Raw variant</th>
                      <th className={`${thClass} text-right`}>Qty</th>
                      <th className={`${thClass} text-right`}>Revenue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {unreportedRows.map((row) => (
                      <tr key={`${row.productGroup}-${row.cleanVariant}-${row.rawVariant}`} className="hover:bg-slate-50">
                        <td className={`${tdClass} font-medium text-slate-800`}>{row.productGroup}</td>
                        <td className={tdClass}>{row.cleanVariant}</td>
                        <td className={`${tdClass} font-mono text-xs text-slate-500`}>{row.rawProduct ?? '—'}</td>
                        <td className={`${tdClass} font-mono text-xs text-slate-500`}>{row.rawVariant}</td>
                        <td className={`${tdClass} text-right`}>{formatNumber(row.totalQty)}</td>
                        <td className={`${tdClass} text-right`}>{formatCurrency(row.totalRevenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-50">
                    <tr>
                      <td colSpan={2} className="px-4 py-2 text-xs font-medium text-slate-500">
                        Unreported totals
                      </td>
                      <td colSpan={2} className="px-4 py-2 text-xs font-medium text-slate-500">
                        {unreportedTotals.rows} rows
                      </td>
                      <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">
                        {formatNumber(unreportedTotals.qty)}
                      </td>
                      <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">
                        {formatCurrency(unreportedTotals.revenue)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </section>
  )
}
