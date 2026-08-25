import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useBatches } from '../hooks/useBatches'
import { formatCurrency, formatNumber } from '../utils/format'
import { ApiError } from '../services/apiClient'
import ErrorBanner from '../components/ErrorBanner'

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function BatchesPage() {
  const { batches, loading, error, remove } = useBatches()
  const navigate = useNavigate()
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function handleConfirmDelete(batchId: string) {
    setDeleting(true)
    setDeleteError(null)
    try {
      await remove(batchId)
      setConfirmDeleteId(null)
    } catch (err) {
      setDeleteError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err))
    } finally {
      setDeleting(false)
    }
  }

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
      {deleteError && <ErrorBanner message={deleteError} onDismiss={() => setDeleteError(null)} />}

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
                <th className="px-4 py-2">Created</th>
                <th className="px-4 py-2 text-right">Qty</th>
                <th className="px-4 py-2 text-right">Revenue</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {batches.map((batch) => {
                const confirming = confirmDeleteId === batch.importBatchId
                return (
                  <tr
                    key={batch.importBatchId}
                    className="cursor-pointer hover:bg-slate-50"
                    onClick={() => navigate(`/batches/${batch.importBatchId}`)}
                  >
                    <td className="px-4 py-2 font-medium text-slate-700">{batch.platform}</td>
                    <td className="px-4 py-2 text-slate-500">
                      {batch.periodStart && batch.periodEnd ? `${batch.periodStart} → ${batch.periodEnd}` : '—'}
                    </td>
                    <td className="px-4 py-2 text-slate-500">{formatDateTime(batch.createdAt)}</td>
                    <td className="px-4 py-2 text-right text-slate-700">{formatNumber(batch.grandTotalQty)}</td>
                    <td className="px-4 py-2 text-right text-slate-700">{formatCurrency(batch.grandTotalRevenue)}</td>
                    <td className="px-4 py-2 text-right" onClick={(event) => event.stopPropagation()}>
                      {confirming ? (
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            disabled={deleting}
                            onClick={() => handleConfirmDelete(batch.importBatchId)}
                            className="rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-60"
                          >
                            {deleting ? 'Deleting…' : 'Delete'}
                          </button>
                          <button
                            type="button"
                            disabled={deleting}
                            onClick={() => setConfirmDeleteId(null)}
                            className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteId(batch.importBatchId)}
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-red-50 hover:text-red-600"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
