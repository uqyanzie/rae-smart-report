import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useBatchDetail } from '../hooks/useBatchDetail'
import { formatCurrency, formatNumber, formatPercent } from '../utils/format'
import type { components } from '../services/api'

type Transform = components['schemas']['TransformResponseDTO']

interface LocationState {
  transform?: Transform
}

const toggleButton = (active: boolean): string =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${
    active ? 'bg-indigo-600 text-white' : 'border border-slate-300 text-slate-600 hover:bg-slate-50'
  }`

const thClass = 'px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500'
const tdClass = 'px-4 py-2 text-slate-700'

export default function BatchDetailPage() {
  const { batchId = '' } = useParams<{ batchId: string }>()
  const location = useLocation()
  const state = location.state as LocationState | null
  const transform = state?.transform
  const [cross, setCross] = useState(false)

  const { data, loading, error } = useBatchDetail(batchId)

  if (loading) {
    return (
      <section>
        <h1 className="text-lg font-semibold text-slate-800">Batch detail</h1>
        <p className="mt-4 text-sm text-slate-500">Loading batch data…</p>
      </section>
    )
  }

  if (error || !data) {
    return (
      <section>
        <h1 className="text-lg font-semibold text-slate-800">Batch detail</h1>
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error ?? 'Batch data unavailable.'}
        </div>
        <Link to="/batches" className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-500">
          ← Back to batches
        </Link>
      </section>
    )
  }

  const variants = cross ? data.crossVariants : data.variants
  const products = cross ? data.crossProducts : data.products
  const datasetQty = variants.reduce((sum, row) => sum + row.totalQty, 0)
  const datasetRevenue = variants.reduce((sum, row) => sum + row.totalRevenue, 0)

  const reportProductCount = transform?.reportedProductCount ?? data.products.length
  const reportQty = transform?.reportedTotalQty ?? data.variants.reduce((sum, row) => sum + row.totalQty, 0)
  const reportRevenue =
    transform?.reportedTotalRevenue ?? data.variants.reduce((sum, row) => sum + row.totalRevenue, 0)
  const hasAudit = Boolean(transform)

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-slate-800">Batch detail</h1>
          <p className="font-mono text-xs text-slate-500">{batchId}</p>
        </div>
        <Link
          to="/batches"
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          ← Batches
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">Platform</p>
          <p className="mt-1 text-lg font-semibold text-slate-800">{transform?.platform ?? '—'}</p>
          <p className="text-xs text-slate-500">
            {transform?.periodStart && transform?.periodEnd
              ? `${transform.periodStart} → ${transform.periodEnd}`
              : 'No period set'}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">Product groups (report)</p>
          <p className="mt-1 text-lg font-semibold text-slate-800">{formatNumber(reportProductCount)}</p>
          <p className="text-xs text-slate-500">cross-bundling excluded</p>
        </div>
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <p className="text-xs font-medium text-indigo-600">Total units (report)</p>
          <p className="mt-1 text-lg font-semibold text-indigo-800">{formatNumber(reportQty)}</p>
          <p className="text-xs text-indigo-500">workbook grid-intersected</p>
        </div>
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <p className="text-xs font-medium text-indigo-600">Total revenue (report)</p>
          <p className="mt-1 text-lg font-semibold text-indigo-800">{formatCurrency(reportRevenue)}</p>
          <p className="text-xs text-indigo-500">workbook grid-intersected</p>
        </div>
      </div>

      {hasAudit && transform && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Audit tally · informational
          </p>
          <div className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-amber-600">Inserted rows</p>
              <p className="font-semibold text-amber-900">{formatNumber(transform.insertedCount)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-600">Skipped rows</p>
              <p className="font-semibold text-amber-900">{formatNumber(transform.skippedCount)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-600">Skipped qty</p>
              <p className="font-semibold text-amber-900">{formatNumber(transform.skippedQty)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-600">Skipped revenue</p>
              <p className="font-semibold text-amber-900">{formatCurrency(transform.skippedRevenue)}</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-amber-700">
            {transform.warningCount} warning(s). Non-zero skipped figures are normal for valid files (dash rows,
            out-of-catalog groups, off-grid variants).
          </p>
        </div>
      )}

      {!hasAudit && (
        <p className="text-xs text-slate-500">
          Tip: the audit tally (inserted / skipped rows) is shown here right after running a transform.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-medium text-slate-600">Cross-bundling rows:</span>
        <button type="button" onClick={() => setCross(false)} className={toggleButton(!cross)}>
          Excluded ({data.variants.length} variants)
        </button>
        <button type="button" onClick={() => setCross(true)} className={toggleButton(cross)}>
          Included ({data.crossVariants.length} variants)
        </button>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Variant breakdown</h2>
        </div>
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
              {variants.map((row) => (
                <tr key={`${row.productGroup}-${row.cleanVariant}`} className="hover:bg-slate-50">
                  <td className={`${tdClass} font-medium text-slate-800`}>{row.productGroup}</td>
                  <td className={tdClass}>{row.cleanVariant}</td>
                  <td className={tdClass}>
                    {row.isBundling && (
                      <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-700">
                        Bundling
                      </span>
                    )}
                    {row.isCrossBundling && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                        Cross
                      </span>
                    )}
                  </td>
                  <td className={`${tdClass} text-right`}>{formatNumber(row.totalQty)}</td>
                  <td className={`${tdClass} text-right`}>{formatCurrency(row.totalRevenue)}</td>
                  <td className={`${tdClass} text-right`}>{formatPercent(row.contributionRatio)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-50">
              <tr>
                <td colSpan={3} className="px-4 py-2 text-xs font-medium text-slate-500">
                  Dataset totals
                </td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">{formatNumber(datasetQty)}</td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">
                  {formatCurrency(datasetRevenue)}
                </td>
                <td className="px-4 py-2" />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Product group summary</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className={thClass}>Product group</th>
                <th className={`${thClass} text-right`}>Qty</th>
                <th className={`${thClass} text-right`}>Revenue</th>
                <th className={`${thClass} text-right`}>Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {products.map((row) => (
                <tr key={row.productGroup} className="hover:bg-slate-50">
                  <td className={`${tdClass} font-medium text-slate-800`}>{row.productGroup}</td>
                  <td className={`${tdClass} text-right`}>{formatNumber(row.totalQty)}</td>
                  <td className={`${tdClass} text-right`}>{formatCurrency(row.totalRevenue)}</td>
                  <td className={`${tdClass} text-right`}>{formatPercent(row.contributionRatio)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-50">
              <tr>
                <td className="px-4 py-2 text-xs font-medium text-slate-500">Total</td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">{formatNumber(datasetQty)}</td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-slate-800">
                  {formatCurrency(datasetRevenue)}
                </td>
                <td className="px-4 py-2" />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </section>
  )
}
