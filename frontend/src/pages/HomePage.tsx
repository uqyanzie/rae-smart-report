import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
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
import { useUploadModal } from '../context/UploadModalContext'
import { formatCurrency, formatNumber, formatPercent } from '../utils/format'
import { getPlatformMeta, shortHash } from '../utils/platform'

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
  '#6366f1',
  '#ec4899',
  '#14b8a6',
  '#f59e0b',
  '#8b5cf6',
  '#3b82f6',
  '#10b981',
  '#f97316',
  '#84cc16',
  '#06b6d4',
  '#a855f7',
  '#ef4444',
]

const PIE_HEIGHT = 480
const RADIAN = Math.PI / 180

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
      fill="#1e293b"
      fontWeight="bold"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={12}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

export default function HomePage() {
  const { batches, loading: batchesLoading, error: batchesError } = useBatches()
  const { openUploadModal } = useUploadModal()
  const [batchId, setBatchId] = useState('')
  const [activeTypes, setActiveTypes] = useState<DashboardFilterType[]>([
    'single',
    'bundling',
    'cross',
  ])
  const [showAllLabels, setShowAllLabels] = useState(false)

  const selectedBatchId = batchId || batches[0]?.importBatchId || ''
  const selectedBatch = useMemo(
    () => batches.find((b) => b.importBatchId === selectedBatchId),
    [batches, selectedBatchId],
  )

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
  const barHeight = Math.max(380, rollups.length * 36 + 60)

  const renderPieTooltip = ({ active, payload }: TooltipContentProps) => {
    if (!active || !payload || payload.length === 0) return null
    const point = payload[0]?.payload as PieSlice | undefined
    if (!point) return null
    return (
      <div className="rounded-lg border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-lg backdrop-blur-xs">
        <p className="font-semibold text-slate-800">
          {formatTooltipLabel(point.name, point.share, showAllLabels)}
        </p>
        <p className="mt-0.5 text-slate-600 font-mono tabular-nums">{formatNumber(point.value)} units</p>
        {point.merged !== undefined && (
          <p className="text-slate-500">{point.merged} product groups merged</p>
        )}
        <p className="mt-0.5 text-indigo-600 font-medium font-mono tabular-nums">{formatPercent(point.share)}</p>
      </div>
    )
  }

  const renderBarTooltip = ({ active, payload }: TooltipContentProps) => {
    if (!active || !payload || payload.length === 0) return null
    const point = payload[0]?.payload as BarPoint | undefined
    if (!point) return null
    return (
      <div className="rounded-lg border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-lg backdrop-blur-xs">
        <p className="font-semibold text-slate-800">
          {formatTooltipLabel(point.name, point.share, showAllLabels)}
        </p>
        <p className="mt-0.5 text-slate-600 font-mono tabular-nums">{formatCurrency(point.revenue)}</p>
        <p className="mt-0.5 text-indigo-600 font-medium font-mono tabular-nums">{formatPercent(point.share)} contribution</p>
      </div>
    )
  }

  const platformMeta = selectedBatch ? getPlatformMeta(selectedBatch.platform) : null

  return (
    <section className="space-y-4">
      {/* Top Section & Compact Batch Control Bar */}
      <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-4">
            {/* Batch Selector */}
            <div className="flex items-center gap-2">
              <label htmlFor="batch-select" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Batch
              </label>
              <select
                id="batch-select"
                value={selectedBatchId}
                onChange={(event) => setBatchId(event.target.value)}
                disabled={batchesLoading || batches.length === 0}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 shadow-xs focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:opacity-50"
              >
                {batches.map((batch) => (
                  <option key={batch.importBatchId} value={batch.importBatchId}>
                    {batch.platform} — {batch.periodStart && batch.periodEnd ? `${batch.periodStart} → ${batch.periodEnd}` : batch.importBatchId.slice(0, 12)} (#{shortHash(batch.importBatchId)})
                  </option>
                ))}
              </select>
            </div>

            {/* Data Types Filter Checklist */}
            <div className="flex items-center gap-2 border-slate-200 pl-0 sm:border-l sm:pl-4">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Types:</span>
              <div className="flex flex-wrap items-center gap-3">
                {FILTER_OPTIONS.map((option) => (
                  <label
                    key={option.key}
                    className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-slate-700 select-none hover:text-slate-900"
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
            </div>
          </div>

          {/* Action Button: Export Workbook */}
          <div className="flex items-center gap-2">
            <Link
              to="/export"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900 transition-colors"
            >
              <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              <span>Export Workbook</span>
            </Link>
          </div>
        </div>
      </div>

      {batchesLoading && <p className="text-sm text-slate-500">Loading batches…</p>}
      {batchesError && <p className="text-sm text-red-600">{batchesError}</p>}
      {!batchesLoading && !batchesError && batches.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <h3 className="mt-3 text-sm font-semibold text-slate-800">No batches yet</h3>
          <p className="mt-1 text-xs text-slate-500">Upload an e-commerce export to start generating sales reports.</p>
          <div className="mt-4">
            <button
              type="button"
              onClick={openUploadModal}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500"
            >
              + Upload Export
            </button>
          </div>
        </div>
      )}

      {selectedBatchId && batches.length > 0 && (
        <>
          {/* Side-by-Side Compact KPI Cards */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Variant rows</span>
                {platformMeta && (
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${platformMeta.badgeClass}`}>
                    {platformMeta.shortLabel}
                  </span>
                )}
              </div>
              <p className="mt-1.5 text-xl font-bold tracking-tight text-slate-800 font-mono tabular-nums">
                {formatNumber(variants.length)}
              </p>
            </div>
            <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 shadow-xs">
              <span className="text-xs font-medium text-indigo-700">Total units</span>
              <p className="mt-1.5 text-xl font-bold tracking-tight text-indigo-900 font-mono tabular-nums">
                {formatNumber(totalQty)}
              </p>
            </div>
            <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 shadow-xs">
              <span className="text-xs font-medium text-indigo-700">Total revenue</span>
              <p className="mt-1.5 text-xl font-bold tracking-tight text-indigo-900 font-mono tabular-nums">
                {formatCurrency(totalRevenue)}
              </p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 shadow-xs">
              <span className="text-xs font-medium text-amber-800">Unreported revenue</span>
              <p className="mt-1.5 text-xl font-bold tracking-tight text-amber-900 font-mono tabular-nums">
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

          {/* Visual Charts */}
          {!loading && !error && rollups.length > 0 && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Contribution Pie Chart */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
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
                      outerRadius="72%"
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
                      wrapperStyle={{ fontSize: 11 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Product Revenue Bar Chart */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                <div className="mb-2 border-b border-slate-100 pb-2">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Product sales (revenue per product group)
                  </h2>
                </div>
                <ResponsiveContainer width="100%" height={Math.min(barHeight, 520)}>
                  <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis
                      type="number"
                      tickFormatter={(value) => formatNumber(Number(value))}
                      tick={{ fontSize: 11 }}
                      stroke="#94a3b8"
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={180}
                      tick={{ fontSize: 11 }}
                      stroke="#94a3b8"
                    />
                    <Tooltip content={renderBarTooltip} />
                    <Bar dataKey="revenue" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Table 1: Variant Breakdown Table with Constrained Viewport Height & Sticky Freeze Columns */}
          {!loading && !error && variants.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 bg-white">
                <div>
                  <h2 className="text-sm font-semibold text-slate-800">Variant Breakdown</h2>
                  <p className="text-xs text-slate-500">
                    Atomic row metrics across {variants.length} active variant records.
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 font-mono tabular-nums">
                  {variants.length} rows
                </span>
              </div>

              <div className="max-h-[calc(100vh-320px)] min-h-[260px] overflow-auto relative">
                <table className="w-full text-left text-sm border-collapse">
                  <thead className="sticky top-0 z-20 bg-slate-100 border-b border-slate-200 shadow-xs">
                    <tr>
                      <th className="sticky left-0 z-30 bg-slate-100 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 border-r border-slate-200">
                        Product group
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600">
                        Variant
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 text-center">
                        Type
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 text-right">
                        Qty
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 text-right">
                        Revenue
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 text-right">
                        Share
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {variants.map((row, idx) => {
                      const share = totalQty > 0 ? row.totalQty / totalQty : 0
                      const isEven = idx % 2 === 1
                      const rowBg = isEven ? 'bg-slate-50/60' : 'bg-white'
                      return (
                        <tr
                          key={`${row.source}-${row.productGroup}-${row.cleanVariant}`}
                          className={`${rowBg} hover:bg-indigo-50/40 transition-colors group`}
                        >
                          <td className={`sticky left-0 z-10 ${rowBg} group-hover:bg-indigo-50/40 px-4 py-2 text-slate-800 font-medium border-r border-slate-200`}>
                            {row.productGroup}
                          </td>
                          <td className="px-4 py-2 text-slate-700">{row.cleanVariant}</td>
                          <td className="px-4 py-2 text-center">
                            <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                              {SOURCE_LABELS[row.source]}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">
                            {formatNumber(row.totalQty)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">
                            {formatCurrency(row.totalRevenue)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-600 font-medium">
                            {formatPercent(share)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot className="sticky bottom-0 z-20 bg-slate-50 border-t border-slate-300 shadow-xs">
                    <tr>
                      <td colSpan={2} className="sticky left-0 z-20 bg-slate-50 px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-slate-700 border-r border-slate-200">
                        Selected Totals ({variants.length} rows)
                      </td>
                      <td className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500">
                        —
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                        {formatNumber(totalQty)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                        {formatCurrency(totalRevenue)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-xs font-bold text-slate-700">
                        100.0%
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}

          {/* Table 2: Unreported Entries Table */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3 bg-white">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">Unreported Entries</h2>
                <p className="text-xs text-slate-500">
                  Persisted but not reported — off-grid variants and non-catalog products.
                </p>
              </div>
              <div className="flex flex-wrap gap-4 text-xs text-slate-600">
                <span>
                  <span className="font-semibold text-slate-800 font-mono tabular-nums">
                    {formatNumber(unreportedTotals.rows)}
                  </span>{' '}
                  rows
                </span>
                <span>
                  <span className="font-semibold text-slate-800 font-mono tabular-nums">
                    {formatNumber(unreportedTotals.qty)}
                  </span>{' '}
                  units
                </span>
                <span>
                  <span className="font-semibold text-slate-800 font-mono tabular-nums">
                    {formatCurrency(unreportedTotals.revenue)}
                  </span>{' '}
                  revenue
                </span>
              </div>
            </div>

            {unreportedLoading && <p className="px-4 py-3 text-sm text-slate-500">Loading unreported entries…</p>}
            {unreportedError && <p className="px-4 py-3 text-sm text-red-600">{unreportedError}</p>}
            {!unreportedLoading && !unreportedError && unreportedRows.length === 0 && (
              <p className="px-4 py-6 text-center text-xs text-slate-500">
                No unreported entries for this batch. All records are matched to catalog master products.
              </p>
            )}
            {!unreportedLoading && !unreportedError && unreportedRows.length > 0 && (
              <div className="max-h-[380px] overflow-auto relative">
                <table className="w-full text-left text-sm border-collapse">
                  <thead className="sticky top-0 z-20 bg-slate-100 border-b border-slate-200 shadow-xs">
                    <tr>
                      <th className="sticky left-0 z-30 bg-slate-100 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 border-r border-slate-200">
                        Product group
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600">
                        Variant
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600">
                        Raw product
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600">
                        Raw variant
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 text-right">
                        Qty
                      </th>
                      <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600 text-right">
                        Revenue
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {unreportedRows.map((row, idx) => {
                      const isEven = idx % 2 === 1
                      const rowBg = isEven ? 'bg-slate-50/60' : 'bg-white'
                      return (
                        <tr
                          key={`${row.productGroup}-${row.cleanVariant}-${row.rawVariant}`}
                          className={`${rowBg} hover:bg-amber-50/40 transition-colors group`}
                        >
                          <td className={`sticky left-0 z-10 ${rowBg} group-hover:bg-amber-50/40 px-4 py-2 text-slate-800 font-medium border-r border-slate-200`}>
                            {row.productGroup}
                          </td>
                          <td className="px-4 py-2 text-slate-700">{row.cleanVariant}</td>
                          <td className="px-4 py-2 font-mono text-xs text-slate-500">{row.rawProduct ?? '—'}</td>
                          <td className="px-4 py-2 font-mono text-xs text-slate-500">{row.rawVariant}</td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">
                            {formatNumber(row.totalQty)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">
                            {formatCurrency(row.totalRevenue)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                  <tfoot className="sticky bottom-0 z-20 bg-slate-50 border-t border-slate-300 shadow-xs">
                    <tr>
                      <td colSpan={2} className="sticky left-0 z-20 bg-slate-50 px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-slate-700 border-r border-slate-200">
                        Unreported totals
                      </td>
                      <td colSpan={2} className="px-4 py-2.5 text-xs font-medium text-slate-500 font-mono tabular-nums">
                        {unreportedTotals.rows} rows
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                        {formatNumber(unreportedTotals.qty)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
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
