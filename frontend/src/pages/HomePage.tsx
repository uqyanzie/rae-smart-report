import { useState } from 'react'
import { useAggregate } from '../hooks/useAggregate'
import { formatCurrency, formatNumber, formatPercent } from '../utils/format'
import PeriodPicker from '../components/PeriodPicker'

const PLATFORM_FILTERS = ['ALL', 'SHOPEE', 'TIKTOK_SHOP'] as const
const CROSS_FILTERS = [
  { label: 'All rows', value: '' },
  { label: 'Excluded', value: '0' },
  { label: 'Included', value: '1' },
] as const

const thClass = 'px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500'
const tdClass = 'px-4 py-2 text-slate-700'

export default function HomePage() {
  const [platform, setPlatform] = useState<string>('ALL')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [cross, setCross] = useState<string>('')

  const { rows, loading, error } = useAggregate(
    platform === 'ALL' ? undefined : platform,
    periodStart || undefined,
    periodEnd || undefined,
    cross === '' ? undefined : Number(cross),
  )

  const totalQty = rows.reduce((sum, row) => sum + row.totalQty, 0)
  const totalRevenue = rows.reduce((sum, row) => sum + row.totalRevenue, 0)

  return (
    <section className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Dashboard</h1>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
            Platform
            <select
              value={platform}
              onChange={(event) => setPlatform(event.target.value)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {PLATFORM_FILTERS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <PeriodPicker start={periodStart} end={periodEnd} onStartChange={setPeriodStart} onEndChange={setPeriodEnd} />
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
            Cross-bundling rows
            <select
              value={cross}
              onChange={(event) => setCross(event.target.value)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {CROSS_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">Filtered rows</p>
          <p className="mt-1 text-lg font-semibold text-slate-800">{formatNumber(rows.length)}</p>
        </div>
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <p className="text-xs font-medium text-indigo-600">Total units</p>
          <p className="mt-1 text-lg font-semibold text-indigo-800">{formatNumber(totalQty)}</p>
        </div>
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <p className="text-xs font-medium text-indigo-600">Total revenue</p>
          <p className="mt-1 text-lg font-semibold text-indigo-800">{formatCurrency(totalRevenue)}</p>
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading aggregate data…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && rows.length === 0 && (
        <p className="text-sm text-slate-500">No rows match the current filters.</p>
      )}

      {!loading && !error && rows.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className={thClass}>Platform</th>
                  <th className={thClass}>Product group</th>
                  <th className={thClass}>Variant</th>
                  <th className={`${thClass} text-right`}>Qty</th>
                  <th className={`${thClass} text-right`}>Revenue</th>
                  <th className={`${thClass} text-right`}>Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={`${row.platform}-${row.productGroup}-${row.cleanVariant}`} className="hover:bg-slate-50">
                    <td className={`${tdClass} font-medium text-slate-800`}>{row.platform}</td>
                    <td className={tdClass}>{row.productGroup}</td>
                    <td className={tdClass}>{row.cleanVariant}</td>
                    <td className={`${tdClass} text-right`}>{formatNumber(row.totalQty)}</td>
                    <td className={`${tdClass} text-right`}>{formatCurrency(row.totalRevenue)}</td>
                    <td className={`${tdClass} text-right`}>{formatPercent(row.contributionRatio)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50">
                <tr>
                  <td colSpan={3} className="px-4 py-2 text-xs font-medium text-slate-500">
                    Filtered totals
                  </td>
                  <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">{formatNumber(totalQty)}</td>
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
    </section>
  )
}
