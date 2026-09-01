interface PeriodPickerProps {
  start: string
  end: string
  onStartChange: (value: string) => void
  onEndChange: (value: string) => void
}

const inputClass =
  'rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

export default function PeriodPicker({ start, end, onStartChange, onEndChange }: PeriodPickerProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
        <span>
          Period start<span className="ml-0.5 text-red-500">*</span>
        </span>
        <input
          type="date"
          required
          className={inputClass}
          value={start}
          onChange={(e) => onStartChange(e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
        <span>
          Period end<span className="ml-0.5 text-red-500">*</span>
        </span>
        <input
          type="date"
          required
          className={inputClass}
          value={end}
          onChange={(e) => onEndChange(e.target.value)}
        />
      </label>
    </div>
  )
}
