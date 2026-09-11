import { useMemo, useState } from 'react'
import { useBatches } from '../hooks/useBatches'
import { apiClient, ApiError } from '../services/apiClient'
import { formatCurrency, formatNumber } from '../utils/format'
import {
  PLATFORM_ORDER,
  batchPeriodKey,
  batchPeriodLabel,
  compareBatchRecency,
  getPlatformMeta,
  shortHash,
  toDateOnly,
  type BatchSummary,
  type PlatformKey,
} from '../utils/platform'
import ErrorBanner from '../components/ErrorBanner'

type ExportMode = 'synced' | 'custom'

interface PlatformExportConfig {
  enabled: boolean
  selectedBatchId: string | null
  includeCaseColours: boolean
}

interface PeriodOption {
  key: string
  label: string
  start: string | null
  platformBatches: Record<string, BatchSummary>
}

interface ActiveSelection {
  platform: string
  batch: BatchSummary
  includeCaseColours: boolean
}

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

function buildPeriodOptions(batches: BatchSummary[]): PeriodOption[] {
  const options = new Map<string, PeriodOption>()
  for (const batch of batches) {
    const key = batchPeriodKey(batch)
    let option = options.get(key)
    if (!option) {
      option = {
        key,
        label: batchPeriodLabel(batch),
        start: toDateOnly(batch.periodStart),
        platformBatches: {},
      }
      options.set(key, option)
    }
    const existing = option.platformBatches[batch.platform]
    if (!existing || compareBatchRecency(batch, existing) < 0) {
      option.platformBatches[batch.platform] = batch
    }
  }
  return [...options.values()].sort((a, b) => {
    if (a.start === null) return 1
    if (b.start === null) return -1
    return b.start.localeCompare(a.start)
  })
}

function buildSyncedConfigs(
  options: PeriodOption[],
  periodKey: string,
  previous: Record<string, PlatformExportConfig>,
): Record<string, PlatformExportConfig> {
  const option = options.find((candidate) => candidate.key === periodKey)
  const next: Record<string, PlatformExportConfig> = {}
  if (option) {
    for (const [platform, batch] of Object.entries(option.platformBatches)) {
      next[platform] = {
        enabled: previous[platform]?.enabled ?? true,
        selectedBatchId: batch.importBatchId,
        includeCaseColours: previous[platform]?.includeCaseColours ?? false,
      }
    }
  }
  // Platforms without a batch in this window stay visible but unavailable.
  for (const [platform, config] of Object.entries(previous)) {
    if (!(platform in next)) {
      next[platform] = { ...config, enabled: false, selectedBatchId: null }
    }
  }
  return next
}

function buildCustomConfigs(
  byPlatform: Record<string, BatchSummary[]>,
  previous: Record<string, PlatformExportConfig>,
): Record<string, PlatformExportConfig> {
  const next: Record<string, PlatformExportConfig> = { ...previous }
  for (const [platform, list] of Object.entries(byPlatform)) {
    const current = previous[platform]
    const stillValid =
      current?.selectedBatchId != null &&
      list.some((batch) => batch.importBatchId === current.selectedBatchId)
    next[platform] = {
      enabled: current?.enabled ?? true,
      selectedBatchId: stillValid ? current!.selectedBatchId : (list[0]?.importBatchId ?? null),
      includeCaseColours: current?.includeCaseColours ?? false,
    }
  }
  return next
}

function PlatformPill({ platform, withLabel = false }: { platform: string; withLabel?: boolean }) {
  const meta = getPlatformMeta(platform)
  return (
    <span
      title={meta.label}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${meta.badgeClass}`}
    >
      <span>{meta.shortLabel}</span>
      {withLabel && <span className="font-medium">{meta.label}</span>}
    </span>
  )
}

export default function ExportPage() {
  const { batches, loading, error } = useBatches()
  const [mode, setMode] = useState<ExportMode>('synced')
  const [selectedPeriodKey, setSelectedPeriodKey] = useState<string | null>(null)
  const [configs, setConfigs] = useState<Record<string, PlatformExportConfig>>({})
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportedFile, setExportedFile] = useState<string | null>(null)

  const platformOrder = useMemo<string[]>(() => {
    const present = new Set(batches.map((batch) => batch.platform))
    const known = PLATFORM_ORDER.filter((platform) => present.has(platform))
    const extras = [...present].filter(
      (platform) => !PLATFORM_ORDER.includes(platform as PlatformKey),
    )
    return [...known, ...extras]
  }, [batches])

  const byPlatform = useMemo<Record<string, BatchSummary[]>>(() => {
    const map: Record<string, BatchSummary[]> = {}
    for (const platform of platformOrder) map[platform] = []
    for (const batch of batches) {
      if (!map[batch.platform]) map[batch.platform] = []
      map[batch.platform].push(batch)
    }
    for (const list of Object.values(map)) list.sort(compareBatchRecency)
    return map
  }, [batches, platformOrder])

  const periodOptions = useMemo(() => buildPeriodOptions(batches), [batches])

  const batchById = useMemo(
    () => new Map(batches.map((batch) => [batch.importBatchId, batch])),
    [batches],
  )

  // Seed the synchronized defaults once the async batch list first arrives.
  // Adjusting state during render (React's sanctioned prop-change pattern)
  // keeps this out of an effect and avoids a cascading second render.
  const [seededBatches, setSeededBatches] = useState<BatchSummary[] | null>(null)
  if (batches.length > 0 && batches !== seededBatches) {
    setSeededBatches(batches)
    const options = buildPeriodOptions(batches)
    const firstKey = options[0]?.key ?? null
    setSelectedPeriodKey(firstKey)
    setConfigs(firstKey ? buildSyncedConfigs(options, firstKey, {}) : {})
  }

  const activeSelections = useMemo<ActiveSelection[]>(() => {
    const selections: ActiveSelection[] = []
    for (const platform of platformOrder) {
      const config = configs[platform]
      if (!config?.enabled || !config.selectedBatchId) continue
      const batch = batchById.get(config.selectedBatchId)
      if (!batch) continue
      selections.push({
        platform,
        batch,
        includeCaseColours:
          config.includeCaseColours && getPlatformMeta(platform).supportsCaseColours,
      })
    }
    return selections
  }, [configs, platformOrder, batchById])

  const totalUnits = activeSelections.reduce((sum, item) => sum + item.batch.grandTotalQty, 0)
  const totalRevenue = activeSelections.reduce(
    (sum, item) => sum + item.batch.grandTotalRevenue,
    0,
  )

  function resetMessages() {
    setExportError(null)
    setExportedFile(null)
  }

  function selectPeriod(key: string) {
    resetMessages()
    setSelectedPeriodKey(key)
    setConfigs((previous) => buildSyncedConfigs(periodOptions, key, previous))
  }

  function changeMode(next: ExportMode) {
    if (next === mode) return
    resetMessages()
    setMode(next)
    if (next === 'custom') {
      setConfigs((previous) => buildCustomConfigs(byPlatform, previous))
    } else {
      setConfigs((previous) =>
        selectedPeriodKey ? buildSyncedConfigs(periodOptions, selectedPeriodKey, previous) : previous,
      )
    }
  }

  function togglePlatform(platform: string) {
    resetMessages()
    setConfigs((previous) => {
      const config = previous[platform]
      if (!config) return previous
      return { ...previous, [platform]: { ...config, enabled: !config.enabled } }
    })
  }

  function selectBatch(platform: string, batchId: string) {
    resetMessages()
    setConfigs((previous) => ({
      ...previous,
      [platform]: {
        ...previous[platform],
        selectedBatchId: batchId || null,
        enabled: batchId ? true : previous[platform].enabled,
      },
    }))
  }

  function toggleCaseColours(platform: string) {
    resetMessages()
    setConfigs((previous) => ({
      ...previous,
      [platform]: {
        ...previous[platform],
        includeCaseColours: !previous[platform].includeCaseColours,
      },
    }))
  }

  async function handleExport() {
    const selections = activeSelections.map((item) => ({
      batchId: item.batch.importBatchId,
      includeCaseColours: item.includeCaseColours,
    }))
    if (selections.length === 0) return
    setExporting(true)
    resetMessages()
    try {
      const { blob, filename } = await apiClient.exportExcel(selections)
      downloadBlob(blob, filename)
      setExportedFile(filename)
    } catch (err) {
      setExportError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err))
    } finally {
      setExporting(false)
    }
  }

  const segmentClass = (active: boolean): string =>
    `rounded px-3 py-1.5 text-xs font-medium transition ${
      active ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
    }`

  const hasBatches = !loading && !error && batches.length > 0

  return (
    <section className="flex flex-col space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-slate-800">Export Workbook</h1>
        <div className="inline-flex rounded-md border border-slate-300 bg-white p-0.5">
          <button type="button" className={segmentClass(mode === 'synced')} onClick={() => changeMode('synced')}>
            Synchronized period
          </button>
          <button type="button" className={segmentClass(mode === 'custom')} onClick={() => changeMode('custom')}>
            Custom per platform
          </button>
        </div>
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

      {hasBatches && (
        <div className="space-y-6 pb-24">
          {mode === 'synced' ? (
            <div className="space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">Reporting period</h2>
                <p className="text-xs text-slate-500">
                  One window applies to every enabled platform. Pick a period to sync all batches at once.
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {periodOptions.map((option) => {
                  const selected = option.key === selectedPeriodKey
                  return (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => selectPeriod(option.key)}
                      className={`rounded-lg border px-4 py-3 text-left transition ${
                        selected
                          ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                          : 'border-slate-200 bg-white hover:border-indigo-300 hover:bg-slate-50'
                      }`}
                    >
                      <span className="block text-sm font-semibold text-slate-800">{option.label}</span>
                      <span className="mt-2 flex flex-wrap gap-1">
                        {Object.keys(option.platformBatches).map((platform) => (
                          <PlatformPill key={platform} platform={platform} />
                        ))}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
              Custom mode: each platform below can use its own batch and date range. Choose a batch per platform.
            </div>
          )}

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">Platforms &amp; batches</h2>
                <p className="text-xs text-slate-500">
                  Toggle a platform to include it, and optionally expand its Produk 2 case colours.
                </p>
              </div>
            </div>

            <ul className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200 bg-white">
              {platformOrder.map((platform) => {
                const meta = getPlatformMeta(platform)
                const config = configs[platform]
                if (!config) return null
                const batch = config.selectedBatchId ? batchById.get(config.selectedBatchId) : undefined
                const platformBatches = byPlatform[platform] ?? []
                return (
                  <li
                    key={platform}
                    className={`flex flex-col gap-3 px-4 py-4 transition sm:flex-row sm:items-center sm:justify-between ${
                      config.enabled ? '' : 'bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={config.enabled}
                        disabled={!config.selectedBatchId}
                        onChange={() => togglePlatform(platform)}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 disabled:cursor-not-allowed"
                      />
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <PlatformPill platform={platform} withLabel />
                        </div>
                        {batch ? (
                          <div className="text-sm text-slate-700">
                            {batchPeriodLabel(batch)}
                            <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-500">
                              #{shortHash(batch.importBatchId)}
                            </span>
                          </div>
                        ) : (
                          <div className="text-sm text-slate-400">
                            {mode === 'synced' ? 'No batch for this period' : 'No batch selected'}
                          </div>
                        )}
                        {mode === 'custom' && platformBatches.length > 0 && (
                          <select
                            value={config.selectedBatchId ?? ''}
                            onChange={(event) => selectBatch(platform, event.target.value)}
                            className="mt-1 max-w-full rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700"
                          >
                            {platformBatches.map((candidate) => (
                              <option key={candidate.importBatchId} value={candidate.importBatchId}>
                                {batchPeriodLabel(candidate)} · #{shortHash(candidate.importBatchId)} ·{' '}
                                {formatNumber(candidate.grandTotalQty)} units
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 pl-7 sm:justify-end sm:pl-0">
                      <div className="min-w-[7rem] text-left sm:text-right">
                        <div className="text-sm font-semibold text-slate-800">
                          {batch ? `${formatNumber(batch.grandTotalQty)} units` : '—'}
                        </div>
                        <div className="text-xs text-slate-500">
                          {batch ? formatCurrency(batch.grandTotalRevenue) : ''}
                        </div>
                      </div>
                      {meta.supportsCaseColours ? (
                        <label
                          className={`flex items-center gap-2 text-xs ${
                            config.enabled && batch ? 'text-slate-600' : 'text-slate-400'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={config.includeCaseColours}
                            disabled={!config.enabled || !batch}
                            onChange={() => toggleCaseColours(platform)}
                            className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 disabled:cursor-not-allowed"
                          />
                          Expand case colours (Produk 2)
                        </label>
                      ) : (
                        <span className="text-xs text-slate-300">Produk 2 not applicable</span>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          </div>

          <div className="sticky bottom-0 z-10 rounded-lg border border-slate-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
                <span className="font-semibold text-slate-800">
                  {activeSelections.length} platform{activeSelections.length === 1 ? '' : 's'} selected
                </span>
                <span className="text-slate-600">
                  Combined units: <span className="font-medium text-slate-800">{formatNumber(totalUnits)}</span>
                </span>
                <span className="text-slate-600">
                  Combined GMV:{' '}
                  <span className="font-medium text-slate-800">{formatCurrency(totalRevenue)}</span>
                </span>
              </div>
              <button
                type="button"
                onClick={handleExport}
                disabled={exporting || activeSelections.length === 0}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {exporting ? 'Preparing workbook…' : 'Export Workbook (.xlsx)'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
