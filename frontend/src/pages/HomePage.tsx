import { useState } from 'react'
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
  XAxis,
  YAxis,
} from 'recharts'
import { useBatches } from '../hooks/useBatches'
import { useBatchDashboard, type DashboardFilterType } from '../hooks/useBatchDashboard'
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
  '#6366f1',
  '#8b5cf6',
  '#06b6d4',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#84cc16',
  '#14b8a6',
  '#f97316',
  '#3b82f6',
  '#a855f7',
]

const PIE_HEIGHT = 560
const RADIAN = Math.PI / 180

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
      fill="#475569"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={11}
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

  const selectedBatchId = batchId || batches[0]?.importBatchId || ''
  const { variants, rollups, totalQty, totalRevenue, loading, error } = useBatchDashboard(
    selectedBatchId,
    activeTypes,
  )

  const toggleType = (key: DashboardFilterType) => {
    setActiveTypes((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    )
  }

  const pieData = rollups.map((row) => ({ name: row.productGroup, value: row.totalQty }))
  const barData = rollups.map((row) => ({ name: row.productGroup, revenue: row.totalRevenue }))
  const barHeight = Math.max(440, rollups.length * 38 + 60)

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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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
                <h2 className="mb-2 text-sm font-semibold text-slate-700">
                  Contribution (units per product group)
                </h2>
                <ResponsiveContainer width="100%" height={PIE_HEIGHT}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="46%"
                      outerRadius="70%"
                      labelLine={{ stroke: '#94a3b8' }}
                      label={renderPieLabel}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatNumber(Number(value))} />
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
                    <Tooltip formatter={(value) => formatCurrency(Number(value))} />
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
        </>
      )}
    </section>
  )
}
