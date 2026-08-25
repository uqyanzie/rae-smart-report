import { useRef, useState } from 'react'

const ACCEPTED_EXTENSIONS = ['xlsx', 'csv']
const MAX_UPLOAD_MB = 50

interface UploadDropzoneProps {
  onFile: (file: File) => void
}

export default function UploadDropzone({ onFile }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleFile(file: File | undefined) {
    if (!file) return
    const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError(`Unsupported format .${extension || '?'} — upload a .xlsx or .csv export.`)
      return
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`File exceeds the ${MAX_UPLOAD_MB} MB upload limit.`)
      return
    }
    setError(null)
    onFile(file)
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a spreadsheet export"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragOver={(event) => {
          event.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragOver(false)
          handleFile(event.dataTransfer.files?.[0])
        }}
        className={`flex min-h-[40vh] cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed p-10 text-center transition-colors ${
          dragOver ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.csv"
          className="hidden"
          onChange={(event) => {
            handleFile(event.target.files?.[0])
            event.target.value = ''
          }}
        />
        <span className="text-3xl" aria-hidden>
          ⬆
        </span>
        <p className="mt-3 text-sm font-medium text-slate-700">Drag &amp; drop your export here, or click to browse</p>
        <p className="mt-1 text-xs text-slate-500">Shopee / TikTok Shop CSV or XLSX export · up to {MAX_UPLOAD_MB} MB</p>
      </div>

      {error && (
        <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
    </div>
  )
}
