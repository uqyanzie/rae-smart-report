import { useState } from 'react'
import type { components } from '../services/api'
import PeriodPicker from './PeriodPicker'

type Ingestion = components['schemas']['IngestionResultDTO']
type Profiler = components['schemas']['ProfilerResponseDTO']
type CleaningRuleDTO = components['schemas']['CleaningRuleDTO']
type ColumnMappingDTO = components['schemas']['ColumnMappingDTO']
type ParentRowIgnoreCondition = components['schemas']['ParentRowIgnoreCondition']
type ParentRowRuleDTO = components['schemas']['ParentRowRuleDTO']
type TransformAndSaveRequestDTO = components['schemas']['TransformAndSaveRequestDTO']

const KNOWN_PLATFORMS = ['SHOPEE', 'TIKTOK_SHOP'] as const

const MAPPING_FIELDS: { key: keyof ColumnMappingDTO; label: string; required: boolean }[] = [
  { key: 'productGroup', label: 'Product group', required: true },
  { key: 'rawVariant', label: 'Raw variant', required: true },
  { key: 'qtySold', label: 'Qty sold', required: true },
  { key: 'revenue', label: 'Revenue', required: true },
  { key: 'sku', label: 'SKU', required: false },
  { key: 'caseColor', label: 'Case color', required: false },
]

const IGNORE_CONDITIONS: ParentRowIgnoreCondition[] = ['EQUALS_DASH', 'IS_EMPTY', 'CONTAINS_TOTAL']

const inputClass =
  'rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

const sectionTitle = 'text-xs font-semibold uppercase tracking-wide text-slate-500'

interface MappingEditorProps {
  ingest: Ingestion
  profile: Profiler
  saving: boolean
  onReprofile: (activeSheet: string) => void
  onSave: (payload: TransformAndSaveRequestDTO) => void
  onReset: () => void
}

export default function MappingEditor({
  ingest,
  profile,
  saving,
  onReprofile,
  onSave,
  onReset,
}: MappingEditorProps) {
  const [activeSheet, setActiveSheet] = useState(ingest.activeSheet)
  const [platform, setPlatform] = useState<string>(
    KNOWN_PLATFORMS.includes(profile.platform as (typeof KNOWN_PLATFORMS)[number]) ? profile.platform : '',
  )
  const [mapping, setMapping] = useState<ColumnMappingDTO>({ ...profile.columnMapping })
  const [parentEnabled, setParentEnabled] = useState(Boolean(profile.parentRowRule))
  const [parentRule, setParentRule] = useState<ParentRowRuleDTO>(
    profile.parentRowRule ?? {
      targetColumn: profile.columnMapping.rawVariant,
      ignoreCondition: 'EQUALS_DASH',
    },
  )
  const [cleaningRules, setCleaningRules] = useState<CleaningRuleDTO[]>(
    profile.suggestedCleaningRules.map((rule) => ({ ...rule })),
  )
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [pendingPayload, setPendingPayload] = useState<TransformAndSaveRequestDTO | null>(null)

  function updateMapping(field: keyof ColumnMappingDTO, value: string) {
    setMapping((current) => ({ ...current, [field]: value }))
  }

  function updateRule(index: number, patch: Partial<CleaningRuleDTO>) {
    setCleaningRules((rules) => rules.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)))
  }

  function buildPayload(): TransformAndSaveRequestDTO | null {
    const problems: string[] = []
    if (!KNOWN_PLATFORMS.includes(platform as (typeof KNOWN_PLATFORMS)[number])) {
      problems.push('Select a platform (SHOPEE or TIKTOK_SHOP).')
    }
    for (const field of MAPPING_FIELDS) {
      if (field.required && !mapping[field.key]?.trim()) {
        problems.push(`${field.label} is required.`)
      }
    }
    if (parentEnabled && !parentRule.targetColumn.trim()) {
      problems.push('Parent-row rule needs a target column.')
    }
    for (const rule of cleaningRules) {
      if (!rule.pattern.trim()) {
        problems.push('Cleaning rule pattern cannot be empty.')
        break
      }
    }
    setErrors(problems)
    if (problems.length > 0) return null

    return {
      fileId: ingest.fileId,
      activeSheet,
      platform,
      periodStart: periodStart || undefined,
      periodEnd: periodEnd || undefined,
      columnMapping: mapping,
      parentRowRule: parentEnabled ? parentRule : null,
      cleaningRules,
      saveAsTemplate: true,
    }
  }

  function handlePrimaryClick() {
    const payload = buildPayload()
    if (payload) setPendingPayload(payload)
  }

  const detectedUnknown = !KNOWN_PLATFORMS.includes(profile.platform as (typeof KNOWN_PLATFORMS)[number])

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-800">{ingest.fileName}</p>
            <p className="text-xs text-slate-500">
              {ingest.totalRows.toLocaleString('id-ID')} rows · {ingest.fileSizeBytes.toLocaleString('id-ID')} bytes
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
            Sheet
            <select
              className={inputClass}
              value={activeSheet}
              onChange={(event) => {
                const sheet = event.target.value
                setActiveSheet(sheet)
                onReprofile(sheet)
              }}
            >
              {ingest.availableSheets.map((sheet) => (
                <option key={sheet} value={sheet}>
                  {sheet}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className={sectionTitle}>Platform</h2>
          {profile.isCached && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
              Template match
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
            Target platform
            <select
              className={inputClass}
              value={KNOWN_PLATFORMS.includes(platform as (typeof KNOWN_PLATFORMS)[number]) ? platform : ''}
              onChange={(event) => setPlatform(event.target.value)}
            >
              <option value="" disabled>
                Select platform…
              </option>
              {KNOWN_PLATFORMS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <p className="text-sm text-slate-600">
            Detected: <span className="font-medium">{profile.platform}</span>
            {!detectedUnknown && (
              <span className="text-slate-500"> · confidence {Math.round(profile.confidence * 100)}%</span>
            )}
          </p>
        </div>
        {detectedUnknown && (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Platform could not be auto-detected from this file. Select one above and map the columns manually.
          </p>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className={`${sectionTitle} mb-3`}>Column mapping</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {MAPPING_FIELDS.map((field) => (
            <label key={field.key} className="flex flex-col gap-1 text-xs font-medium text-slate-600">
              <span>
                {field.label}
                {field.required && <span className="ml-0.5 text-red-500">*</span>}
              </span>
              <input
                list={`mapping-headers-${field.key}`}
                className={inputClass}
                value={mapping[field.key] ?? ''}
                onChange={(event) => updateMapping(field.key, event.target.value)}
                placeholder={field.required ? 'Raw column header…' : '— none —'}
              />
              <datalist id={`mapping-headers-${field.key}`}>
                {ingest.rawHeaders.map((header) => (
                  <option key={header} value={header} />
                ))}
              </datalist>
            </label>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className={sectionTitle}>Parent-row pruning</h2>
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
            <input
              type="checkbox"
              checked={parentEnabled}
              onChange={(event) => setParentEnabled(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            Enabled
          </label>
        </div>
        {parentEnabled && (
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
              Target column
              <input
                list="parent-target-headers"
                className={inputClass}
                value={parentRule.targetColumn}
                onChange={(event) => setParentRule((rule) => ({ ...rule, targetColumn: event.target.value }))}
              />
              <datalist id="parent-target-headers">
                {ingest.rawHeaders.map((header) => (
                  <option key={header} value={header} />
                ))}
              </datalist>
            </label>
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
              Ignore condition
              <select
                className={inputClass}
                value={parentRule.ignoreCondition}
                onChange={(event) =>
                  setParentRule((rule) => ({ ...rule, ignoreCondition: event.target.value as ParentRowIgnoreCondition }))
                }
              >
                {IGNORE_CONDITIONS.map((condition) => (
                  <option key={condition} value={condition}>
                    {condition}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className={sectionTitle}>Cleaning rules</h2>
          <button
            type="button"
            onClick={() => setCleaningRules((rules) => [...rules, { pattern: '', replacement: '', description: '' }])}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            + Add rule
          </button>
        </div>
        {cleaningRules.length === 0 && <p className="text-sm text-slate-500">No cleaning rules.</p>}
        {cleaningRules.map((rule, index) => (
          <div key={index} className="mb-2 flex flex-wrap items-end gap-2">
            <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs font-medium text-slate-600">
              Pattern (regex)
              <input
                className={inputClass}
                value={rule.pattern}
                onChange={(event) => updateRule(index, { pattern: event.target.value })}
                placeholder="e.g. ^\d+\.\s*"
              />
            </label>
            <label className="flex min-w-28 flex-col gap-1 text-xs font-medium text-slate-600">
              Replacement
              <input
                className={inputClass}
                value={rule.replacement}
                onChange={(event) => updateRule(index, { replacement: event.target.value })}
              />
            </label>
            <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs font-medium text-slate-600">
              Description
              <input
                className={inputClass}
                value={rule.description}
                onChange={(event) => updateRule(index, { description: event.target.value })}
                placeholder="Why this rule?"
              />
            </label>
            <button
              type="button"
              onClick={() => setCleaningRules((rules) => rules.filter((_, i) => i !== index))}
              className="rounded-md border border-red-200 px-2 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className={`${sectionTitle} mb-3`}>Reporting period</h2>
        <PeriodPicker
          start={periodStart}
          end={periodEnd}
          onStartChange={setPeriodStart}
          onEndChange={setPeriodEnd}
        />
      </div>

      {ingest.sampleRows && ingest.sampleRows.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <h2 className={`${sectionTitle} mb-3`}>Sample data</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                <tr>
                  {ingest.rawHeaders.map((header) => (
                    <th key={header} className="px-3 py-2 whitespace-nowrap">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ingest.sampleRows.slice(0, 5).map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {ingest.rawHeaders.map((header) => (
                      <td key={header} className="px-3 py-2 whitespace-nowrap text-slate-600">
                        {row[header] === null || row[header] === undefined ? '' : String(row[header])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <ul className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errors.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}

      {pendingPayload && (
        <div className="rounded-md border border-indigo-200 bg-indigo-50 px-4 py-3">
          <p className="text-sm text-indigo-900">
            Run the transform for <span className="font-semibold">{pendingPayload.platform}</span>? This persists a
            batch, caches the mapping template, and opens the report results.
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                onSave(pendingPayload)
                setPendingPayload(null)
              }}
              disabled={saving}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? 'Running…' : 'Run transform'}
            </button>
            <button
              type="button"
              onClick={() => setPendingPayload(null)}
              disabled={saving}
              className="rounded-md border border-indigo-300 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-60"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-200 pt-4">
        <button
          type="button"
          onClick={onReset}
          disabled={saving}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
        >
          Start over
        </button>
        <button
          type="button"
          onClick={handlePrimaryClick}
          disabled={saving}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? 'Running…' : 'Run transform & save'}
        </button>
      </div>
      <p className="text-right text-xs text-slate-500">
        Running the transform persists a batch, caches the mapping template (so matching re-uploads are auto-detected),
        and opens the report results with the audit tally.
      </p>
    </div>
  )
}
