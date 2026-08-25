import { Link } from 'react-router-dom'
import { useBatches } from '../hooks/useBatches'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(value)
}

export default function BatchesPage() {
  const { batches, loading, error } = useBatches()

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-800">Batches</h1>
        <Link
          to="/upload"
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
        >
          Upload export
        </Link>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading batches…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && batches.length === 0 && (
        <p className="text-sm text-slate-500">
          No batches yet. Run a transform from the Upload screen, then return here.
        </p>
      )}

      {!loading && !error && batches.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Platform</th>
                <th className="px-4 py-2">Period</th>
                <th className="px-4 py-2 text-right">Qty</th>
                <th className="px-4 py-2 text-right">Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {batches.map((batch) => (
                <tr key={batch.importBatchId} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{batch.platform}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {batch.periodStart && batch.periodEnd ? `${batch.periodStart} → ${batch.periodEnd}` : '—'}
                  </td>
                  <td className="px-4 py-2 text-right text-slate-700">{batch.grandTotalQty.toLocaleString('id-ID')}</td>
                  <td className="px-4 py-2 text-right text-slate-700">{formatCurrency(batch.grandTotalRevenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
