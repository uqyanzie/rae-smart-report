import { useState } from 'react'
import { useBatches } from '../hooks/useBatches'
import { apiClient, ApiError } from '../services/apiClient'
import { formatCurrency, formatNumber } from '../utils/format'
import ErrorBanner from '../components/ErrorBanner'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export default function ExportPage() {
  const { batches, loading, error } = useBatches()
  const [selectedByPlatform, setSelectedByPlatform] = useState<Record<string, string>>({})
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportedFile, setExportedFile] = useState<string | null>(null)
  const [includeCaseColors, setIncludeCaseColors] = useState(false)

  const platforms = Array.from(new Set(batches.map((batch) => batch.platform)))

  function toggleBatch(batchId: string, platform: string) {
    setExportError(null)
    setExportedFile(null)
    setSelectedByPlatform((current) => {
      const next = { ...current }
      if (next[platform] === batchId) {
        delete next[platform]
      } else {
        next[platform] = batchId
      }
      return next
    })
  }

  async function handleExport() {
    const selectedIds = Object.values(selectedByPlatform)
    if (selectedIds.length === 0) return
    setExporting(true)
    setExportError(null)
    setExportedFile(null)
    try {
      const { blob, filename } = await apiClient.exportExcel(selectedIds, includeCaseColors)
      downloadBlob(blob, filename)
      setExportedFile(filename)
    } catch (err) {
      setExportError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err))
    } finally {
      setExporting(false)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-slate-800">Export Excel</h1>
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting || Object.keys(selectedByPlatform).length === 0}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {exporting ? 'Preparing workbook…' : 'Export workbook'}
        </button>
      </div>

      {exportError && <ErrorBanner message={exportError} onDismiss={() => setExportError(null)} />}
      {exportedFile && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Downloaded <span className="font-semibold">{exportedFile}</span> — it should open with the report sheets.
        </div>
      )}

      {loading && <p className="text-sm text-slate-500">Loading batches…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && batches.length === 0 && (
        <p className="text-sm text-slate-500">
          No batches to export yet. Run a transform from the Upload screen, then return here.
        </p>
      )}

      {!loading && !error && batches.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Select one batch per platform. Exactly one batch per platform is exported (Shopee, TikTok Shop, Tokopedia
            and/or Lazada) — selecting a second batch for the same platform replaces the first.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {platforms.map((platform) => (
              <div key={platform} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                <div className="border-b border-slate-200 px-4 py-3">
                  <h2 className="text-sm font-semibold text-slate-800">{platform}</h2>
                </div>
                <ul className="divide-y divide-slate-100">
                  {batches
                    .filter((batch) => batch.platform === platform)
                    .map((batch) => {
                      const checked = selectedByPlatform[platform] === batch.importBatchId
                      return (
                        <li key={batch.importBatchId}>
                          <label
                            className={`flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-slate-50 ${
                              checked ? 'bg-indigo-50' : ''
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleBatch(batch.importBatchId, platform)}
                              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                            />
                            <span className="flex-1">
                              <span className="block font-mono text-xs text-slate-500">{batch.importBatchId}</span>
                              <span className="block text-sm text-slate-700">
                                {batch.periodStart && batch.periodEnd
                                  ? `${batch.periodStart} → ${batch.periodEnd}`
                                  : 'No period set'}
                              </span>
                            </span>
                            <span className="text-right">
                              <span className="block text-sm font-semibold text-slate-800">
                                {formatNumber(batch.grandTotalQty)} units
                              </span>
                              <span className="block text-xs text-slate-500">{formatCurrency(batch.grandTotalRevenue)}</span>
                            </span>
                          </label>
                        </li>
                      )
                    })}
                </ul>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={includeCaseColors}
                onChange={(event) => {
                  setIncludeCaseColors(event.target.checked)
                  setExportedFile(null)
                }}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Include case colours (Produk 2 · Tinted Jelly Balm)
            </label>
            <p className="mt-1 text-xs text-slate-500">
              When enabled, the Produk 2 cross-bundling groups that involve Tinted Jelly Balm are
              expanded into one row per case colour (plus a case-less catch-all row per shade pair).
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Selected:{' '}
              {Object.keys(selectedByPlatform).length === 0 ? (
                <span className="text-slate-400">none</span>
              ) : (
                <span className="font-medium text-slate-800">
                  {Object.keys(selectedByPlatform).join(', ')}
                </span>
              )}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              The workbook contains the Produk sheets for each selected platform, the Produk 2 (cross-bundling) sheets
              for Shopee and TikTok Shop, and the per-platform unreported sheets.
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
