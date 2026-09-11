import type { components } from '../services/api'

export type BatchSummary = components['schemas']['BatchSummaryDTO']

export type PlatformKey = 'SHOPEE' | 'TIKTOK_SHOP' | 'TOKOPEDIA' | 'LAZADA'

export interface PlatformMeta {
  label: string
  shortLabel: string
  badgeClass: string
  supportsCaseColours: boolean
}

export const PLATFORM_ORDER: PlatformKey[] = ['SHOPEE', 'TIKTOK_SHOP', 'TOKOPEDIA', 'LAZADA']

const PLATFORM_META: Record<PlatformKey, PlatformMeta> = {
  SHOPEE: {
    label: 'Shopee',
    shortLabel: 'SP',
    badgeClass: 'bg-orange-100 text-orange-700',
    supportsCaseColours: true,
  },
  TIKTOK_SHOP: {
    label: 'TikTok Shop',
    shortLabel: 'TT',
    badgeClass: 'bg-slate-800 text-white',
    supportsCaseColours: true,
  },
  TOKOPEDIA: {
    label: 'Tokopedia',
    shortLabel: 'TP',
    badgeClass: 'bg-emerald-100 text-emerald-700',
    supportsCaseColours: false,
  },
  LAZADA: {
    label: 'Lazada',
    shortLabel: 'LZ',
    badgeClass: 'bg-blue-100 text-blue-700',
    supportsCaseColours: false,
  },
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MONTHS_FULL = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

export function getPlatformMeta(platform: string): PlatformMeta {
  return (
    PLATFORM_META[platform as PlatformKey] ?? {
      label: platform,
      shortLabel: platform.slice(0, 2).toUpperCase(),
      badgeClass: 'bg-slate-200 text-slate-700',
      supportsCaseColours: false,
    }
  )
}

export function toDateOnly(value: string | null | undefined): string | null {
  if (!value) return null
  const [datePart] = value.split('T')
  return datePart || null
}

function parseParts(dateOnly: string): { year: number; month: number; day: number } {
  const [year, month, day] = dateOnly.split('-').map(Number)
  return { year, month, day }
}

function padDay(day: number): string {
  return String(day).padStart(2, '0')
}

function formatDayMonth(dateOnly: string): string {
  const { month, day } = parseParts(dateOnly)
  return `${padDay(day)} ${MONTHS[month - 1]}`
}

export function formatPeriodLabel(start: string, end: string): string {
  if (start === end) {
    return `${formatDayMonth(start)} ${parseParts(start).year}`
  }
  const s = parseParts(start)
  const e = parseParts(end)
  // A first-of-month to last-of-month span is surfaced as a monthly report.
  if (s.year === e.year && s.month === e.month && s.day === 1) {
    const lastDay = new Date(Date.UTC(e.year, e.month, 0)).getUTCDate()
    if (e.day === lastDay) {
      return `${MONTHS_FULL[e.month - 1]} ${e.year} (Monthly)`
    }
  }
  const left = formatDayMonth(start)
  const right = `${formatDayMonth(end)} ${e.year}`
  return `${left} – ${right}`
}

export function batchPeriodKey(batch: BatchSummary): string {
  const start = toDateOnly(batch.periodStart)
  const end = toDateOnly(batch.periodEnd)
  if (!start || !end) return '__no_period__'
  return `${start}_${end}`
}

export function batchPeriodLabel(batch: BatchSummary): string {
  const start = toDateOnly(batch.periodStart)
  const end = toDateOnly(batch.periodEnd)
  if (!start || !end) return 'No period set'
  return formatPeriodLabel(start, end)
}

export function shortHash(batchId: string): string {
  const parts = batchId.split('-')
  return parts[parts.length - 1] || batchId
}

export function compareBatchRecency(a: BatchSummary, b: BatchSummary): number {
  const aStart = toDateOnly(a.periodStart) ?? ''
  const bStart = toDateOnly(b.periodStart) ?? ''
  if (aStart !== bStart) return bStart.localeCompare(aStart)
  const aCreated = a.createdAt ?? ''
  const bCreated = b.createdAt ?? ''
  return bCreated.localeCompare(aCreated)
}
