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
  `rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
    active
      ? 'bg-indigo-600 text-white shadow-xs'
      : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
  }`

export default function BatchDetailPage() {
  const { batchId = '' } = useParams<{ batchId: string }>()
  const location = useLocation()
  const state = location.state as LocationState | null
  const transform = state?.transform
  const [cross, setCross] = useState(false)

  const { data, loading, error } = useBatchDetail(batchId)

  if (loading) {
    return (
      <section className="space-y-4">
        <h1 className="text-lg font-semibold text-slate-800">Batch detail</h1>
        <p className="text-sm text-slate-500">Loading batch data…</p>
      </section>
    )
  }

  if (error || !data) {
    return (
      <section className="space-y-4">
        <h1 className="text-lg font-semibold text-slate-800">Batch detail</h1>
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error ?? 'Batch data unavailable.'}
        </div>
        <Link to="/batches" className="inline-block text-sm font-medium text-indigo-600 hover:text-indigo-500">
          ← Back to batches
        </Link>
      </section>
    )
  }

  const variants = cross ? data.crossVariants : data.variants
  const products = cross ? data.crossProducts : data.products
  const datasetQty = variants.reduce((sum, row) => sum + row.totalQty, 0)
  const datasetRevenue = variants.reduce((sum, row) => sum + row.totalRevenue, 0)
  const unreportedQty = data.unreported.reduce((sum, row) => sum + row.totalQty, 0)
  const unreportedRevenue = data.unreported.reduce((sum, row) => sum + row.totalRevenue, 0)

  const reportProductCount = transform?.reportedProductCount ?? data.products.length
  const reportQty = transform?.reportedTotalQty ?? data.variants.reduce((sum, row) => sum + row.totalQty, 0)
  const reportRevenue =
    transform?.reportedTotalRevenue ?? data.variants.reduce((sum, row) => sum + row.totalRevenue, 0)
  const hasAudit = Boolean(transform)

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-slate-800">Batch Detail</h1>
          <p className="font-mono text-xs text-slate-500">{batchId}</p>
        </div>
        <Link
          to="/batches"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 transition-colors"
        >
          ← Batches
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Platform</p>
          <p className="mt-1 text-lg font-bold text-slate-800">{transform?.platform ?? '—'}</p>
          <p className="text-xs text-slate-500">
            {transform?.periodStart && transform?.periodEnd
              ? `${transform.periodStart} → ${transform.periodEnd}`
              : 'No period set'}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Product groups (report)</p>
          <p className="mt-1 text-lg font-bold text-slate-800 font-mono tabular-nums">{formatNumber(reportProductCount)}</p>
          <p className="text-xs text-slate-500">cross-bundling excluded</p>
        </div>
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 shadow-xs">
          <p className="text-xs font-medium text-indigo-700">Total units (report)</p>
          <p className="mt-1 text-lg font-bold text-indigo-900 font-mono tabular-nums">{formatNumber(reportQty)}</p>
          <p className="text-xs text-indigo-500">workbook grid-intersected</p>
        </div>
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 shadow-xs">
          <p className="text-xs font-medium text-indigo-700">Total revenue (report)</p>
          <p className="mt-1 text-lg font-bold text-indigo-900 font-mono tabular-nums">{formatCurrency(reportRevenue)}</p>
          <p className="text-xs text-indigo-500">workbook grid-intersected</p>
        </div>
      </div>

      {hasAudit && transform && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 shadow-xs">
          <p className="text-xs font-bold uppercase tracking-wider text-amber-800">
            Audit Tally · Informational
          </p>
          <div className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-amber-700">Inserted rows</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatNumber(transform.insertedCount)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Skipped rows (dash only)</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatNumber(transform.skippedCount)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Skipped qty</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatNumber(transform.skippedQty)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Skipped revenue</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatCurrency(transform.skippedRevenue)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Unreported rows</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatNumber(transform.unreportedCount)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Unreported qty</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatNumber(transform.unreportedQty)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Unreported revenue</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatCurrency(transform.unreportedRevenue)}</p>
            </div>
            <div>
              <p className="text-xs text-amber-700">Warnings</p>
              <p className="font-bold text-amber-950 font-mono tabular-nums">{formatNumber(transform.warningCount)}</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-amber-700">
            Skipped rows are dash/empty parent summaries only (never persisted). Unreported entries —
            off-grid variants and non-catalog products — are persisted and shown in the "Unreported
            entries" section below, never in a report figure.
          </p>
        </div>
      )}

      {!hasAudit && (
        <p className="text-xs text-slate-500">
          Tip: the audit tally (inserted / skipped rows) is shown here right after running a transform.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Cross-bundling rows:</span>
        <button type="button" onClick={() => setCross(false)} className={toggleButton(!cross)}>
          Excluded ({data.variants.length} variants)
        </button>
        <button type="button" onClick={() => setCross(true)} className={toggleButton(cross)}>
          Included ({data.crossVariants.length} variants)
        </button>
      </div>

      {/* Variant breakdown */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3 bg-white">
          <h2 className="text-sm font-semibold text-slate-800">Variant Breakdown</h2>
        </div>
        <div className="max-h-[380px] overflow-auto relative">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="sticky top-0 z-20 bg-slate-100 text-xs font-semibold uppercase tracking-wider text-slate-600 border-b border-slate-200 shadow-xs">
              <tr>
                <th className="sticky left-0 z-30 bg-slate-100 px-4 py-2.5 border-r border-slate-200">Product group</th>
                <th className="px-4 py-2.5">Variant</th>
                <th className="px-4 py-2.5 text-center">Type</th>
                <th className="px-4 py-2.5 text-right">Qty</th>
                <th className="px-4 py-2.5 text-right">Revenue</th>
                <th className="px-4 py-2.5 text-right">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {variants.map((row, idx) => {
                const isEven = idx % 2 === 1
                const rowBg = isEven ? 'bg-slate-50/60' : 'bg-white'
                return (
                  <tr key={`${row.productGroup}-${row.cleanVariant}`} className={`${rowBg} hover:bg-indigo-50/40 transition-colors group`}>
                    <td className={`sticky left-0 z-10 ${rowBg} group-hover:bg-indigo-50/40 px-4 py-2 font-medium text-slate-800 border-r border-slate-200`}>
                      {row.productGroup}
                    </td>
                    <td className="px-4 py-2 text-slate-700">{row.cleanVariant}</td>
                    <td className="px-4 py-2 text-center">
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
                      {!row.isBundling && !row.isCrossBundling && (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                          Single
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">{formatNumber(row.totalQty)}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">{formatCurrency(row.totalRevenue)}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-600 font-medium">{formatPercent(row.contributionRatio)}</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot className="sticky bottom-0 z-20 bg-slate-50 border-t border-slate-300 shadow-xs">
              <tr>
                <td colSpan={3} className="sticky left-0 z-20 bg-slate-50 px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-slate-700 border-r border-slate-200">
                  Dataset totals ({variants.length} rows)
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">{formatNumber(datasetQty)}</td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                  {formatCurrency(datasetRevenue)}
                </td>
                <td className="px-4 py-2.5" />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Product group summary */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3 bg-white">
          <h2 className="text-sm font-semibold text-slate-800">Product Group Summary</h2>
        </div>
        <div className="max-h-[340px] overflow-auto relative">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="sticky top-0 z-20 bg-slate-100 text-xs font-semibold uppercase tracking-wider text-slate-600 border-b border-slate-200 shadow-xs">
              <tr>
                <th className="sticky left-0 z-30 bg-slate-100 px-4 py-2.5 border-r border-slate-200">Product group</th>
                <th className="px-4 py-2.5 text-right">Qty</th>
                <th className="px-4 py-2.5 text-right">Revenue</th>
                <th className="px-4 py-2.5 text-right">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {products.map((row, idx) => {
                const isEven = idx % 2 === 1
                const rowBg = isEven ? 'bg-slate-50/60' : 'bg-white'
                return (
                  <tr key={row.productGroup} className={`${rowBg} hover:bg-indigo-50/40 transition-colors group`}>
                    <td className={`sticky left-0 z-10 ${rowBg} group-hover:bg-indigo-50/40 px-4 py-2 font-medium text-slate-800 border-r border-slate-200`}>
                      {row.productGroup}
                    </td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">{formatNumber(row.totalQty)}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">{formatCurrency(row.totalRevenue)}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-600 font-medium">{formatPercent(row.contributionRatio)}</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot className="sticky bottom-0 z-20 bg-slate-50 border-t border-slate-300 shadow-xs">
              <tr>
                <td className="sticky left-0 z-20 bg-slate-50 px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-slate-700 border-r border-slate-200">Total</td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">{formatNumber(datasetQty)}</td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                  {formatCurrency(datasetRevenue)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-xs font-bold text-slate-700">100.0%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Unreported entries */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3 bg-white">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Unreported Entries</h2>
            <p className="text-xs text-slate-500">
              Persisted but not reported — off-grid variants and non-catalog products
            </p>
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-slate-600">
            <span>
              <span className="font-semibold text-slate-800 font-mono tabular-nums">{formatNumber(data.unreported.length)}</span> rows
            </span>
            <span>
              <span className="font-semibold text-slate-800 font-mono tabular-nums">{formatNumber(unreportedQty)}</span> units
            </span>
            <span>
              <span className="font-semibold text-slate-800 font-mono tabular-nums">{formatCurrency(unreportedRevenue)}</span> revenue
            </span>
          </div>
        </div>
        {data.unreported.length === 0 ? (
          <p className="px-4 py-6 text-center text-xs text-slate-500">No unreported entries for this batch.</p>
        ) : (
          <div className="max-h-[340px] overflow-auto relative">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="sticky top-0 z-20 bg-slate-100 text-xs font-semibold uppercase tracking-wider text-slate-600 border-b border-slate-200 shadow-xs">
                <tr>
                  <th className="sticky left-0 z-30 bg-slate-100 px-4 py-2.5 border-r border-slate-200">Product group</th>
                  <th className="px-4 py-2.5">Variant</th>
                  <th className="px-4 py-2.5">Raw product</th>
                  <th className="px-4 py-2.5">Raw variant</th>
                  <th className="px-4 py-2.5 text-right">Qty</th>
                  <th className="px-4 py-2.5 text-right">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.unreported.map((row, idx) => {
                  const isEven = idx % 2 === 1
                  const rowBg = isEven ? 'bg-slate-50/60' : 'bg-white'
                  return (
                    <tr
                      key={`${row.productGroup}-${row.cleanVariant}-${row.rawVariant}`}
                      className={`${rowBg} hover:bg-amber-50/40 transition-colors group`}
                    >
                      <td className={`sticky left-0 z-10 ${rowBg} group-hover:bg-amber-50/40 px-4 py-2 font-medium text-slate-800 border-r border-slate-200`}>
                        {row.productGroup}
                      </td>
                      <td className="px-4 py-2 text-slate-700">{row.cleanVariant}</td>
                      <td className="px-4 py-2 font-mono text-xs text-slate-500">{row.rawProduct ?? '—'}</td>
                      <td className="px-4 py-2 font-mono text-xs text-slate-500">{row.rawVariant}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">{formatNumber(row.totalQty)}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums text-slate-800">{formatCurrency(row.totalRevenue)}</td>
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
                    {data.unreported.length} rows
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                    {formatNumber(unreportedQty)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm font-bold text-slate-900">
                    {formatCurrency(unreportedRevenue)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
