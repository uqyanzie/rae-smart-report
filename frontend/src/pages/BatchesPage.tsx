import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBatches } from '../hooks/useBatches'
import { useUploadModal } from '../context/UploadModalContext'
import { formatCurrency, formatNumber } from '../utils/format'
import { getPlatformMeta, shortHash } from '../utils/platform'
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
  const { openUploadModal } = useUploadModal()
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
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-800">Batches</h1>
          <p className="text-xs text-slate-500">History of ingested sales exports and persisted batch data.</p>
        </div>
        <button
          type="button"
          onClick={openUploadModal}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span>Upload Export</span>
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading batches…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {deleteError && <ErrorBanner message={deleteError} onDismiss={() => setDeleteError(null)} />}

      {!loading && !error && batches.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <h3 className="text-sm font-semibold text-slate-800">No batches yet</h3>
          <p className="mt-1 text-xs text-slate-500">Upload an export to begin analyzing your sales data.</p>
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

      {!loading && !error && batches.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="max-h-[calc(100vh-240px)] overflow-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="sticky top-0 z-10 bg-slate-100 text-xs font-semibold uppercase tracking-wider text-slate-600 border-b border-slate-200 shadow-xs">
                <tr>
                  <th className="px-4 py-2.5">Platform</th>
                  <th className="px-4 py-2.5">Batch ID</th>
                  <th className="px-4 py-2.5">Period</th>
                  <th className="px-4 py-2.5">Created</th>
                  <th className="px-4 py-2.5 text-right">Qty</th>
                  <th className="px-4 py-2.5 text-right">Revenue</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {batches.map((batch, idx) => {
                  const confirming = confirmDeleteId === batch.importBatchId
                  const meta = getPlatformMeta(batch.platform)
                  const isEven = idx % 2 === 1
                  const rowBg = isEven ? 'bg-slate-50/60' : 'bg-white'
                  return (
                    <tr
                      key={batch.importBatchId}
                      className={`${rowBg} cursor-pointer hover:bg-indigo-50/40 transition-colors`}
                      onClick={() => navigate(`/batches/${batch.importBatchId}`)}
                    >
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${meta.badgeClass}`}>
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        #{shortHash(batch.importBatchId)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {batch.periodStart && batch.periodEnd ? `${batch.periodStart} → ${batch.periodEnd}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 font-mono tabular-nums">{formatDateTime(batch.createdAt)}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold text-slate-800">
                        {formatNumber(batch.grandTotalQty)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold text-slate-800">
                        {formatCurrency(batch.grandTotalRevenue)}
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(event) => event.stopPropagation()}>
                        {confirming ? (
                          <div className="flex justify-end gap-1.5">
                            <button
                              type="button"
                              disabled={deleting}
                              onClick={() => handleConfirmDelete(batch.importBatchId)}
                              className="rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-60"
                            >
                              {deleting ? 'Deleting…' : 'Confirm'}
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
                            className="rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-600 hover:border-red-200 hover:bg-red-50 hover:text-red-600 transition-colors"
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
        </div>
      )}
    </section>
  )
}
