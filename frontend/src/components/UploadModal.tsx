import { useEffect, useRef } from 'react'
import ErrorBanner from './ErrorBanner'
import MappingEditor from './MappingEditor'
import UploadDropzone from './UploadDropzone'
import { useUploadFlow } from '../hooks/useUploadFlow'
import type { components } from '../services/api'

type Transform = components['schemas']['TransformResponseDTO']

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (batchId: string, transform: Transform) => void
}

function UploadingPanel({ progress }: { progress: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>Uploading…</span>
        <span>{progress}%</span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full bg-indigo-600 transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}

function ProfilingPanel() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center gap-3 text-sm text-slate-600">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
        Detecting platform &amp; mapping…
      </div>
    </div>
  )
}

export default function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const { step, error, saving, upload, reprofile, runTransform, reset, dismissError } = useUploadFlow()
  const modalRef = useRef<HTMLDivElement | null>(null)

  // Reset state whenever the modal closes
  useEffect(() => {
    if (!isOpen) {
      reset()
    }
  }, [isOpen, reset])

  // Trap Escape key & lock body scroll while modal is open
  useEffect(() => {
    if (!isOpen) return

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  // Handle successful transform save
  useEffect(() => {
    if (step.kind === 'saved') {
      onSuccess?.(step.transform.importBatchId, step.transform)
      onClose()
    }
  }, [step, onSuccess, onClose])

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog Body */}
      <div
        ref={modalRef}
        className="relative z-10 flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-slate-50 shadow-2xl ring-1 ring-black/10"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <h2 id="upload-modal-title" className="text-base font-semibold text-slate-800">
              Upload Sales Export
            </h2>
            <p className="text-xs text-slate-500">
              Upload Shopee / TikTok CSV or XLSX, review column mapping, and import.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Close modal"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div className="overflow-y-auto p-6 space-y-4">
          {error && <ErrorBanner message={error} onDismiss={dismissError} />}

          {step.kind === 'idle' && <UploadDropzone onFile={upload} />}

          {step.kind === 'uploading' && <UploadingPanel progress={step.progress} />}

          {step.kind === 'profiling' && <ProfilingPanel />}

          {step.kind === 'review' && (
            <MappingEditor
              ingest={step.ingest}
              profile={step.profile}
              saving={saving}
              onReprofile={(sheet) => reprofile(step.ingest, sheet, step.profile)}
              onSave={runTransform}
              onReset={reset}
            />
          )}
        </div>
      </div>
    </div>
  )
}
