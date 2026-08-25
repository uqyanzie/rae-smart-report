import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ErrorBanner from '../components/ErrorBanner'
import MappingEditor from '../components/MappingEditor'
import UploadDropzone from '../components/UploadDropzone'
import { useUploadFlow } from '../hooks/useUploadFlow'

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

export default function UploadPage() {
  const { step, error, saving, upload, reprofile, runTransform, reset, dismissError } = useUploadFlow()
  const navigate = useNavigate()

  useEffect(() => {
    if (step.kind === 'saved') {
      navigate(`/batches/${step.transform.importBatchId}`, { state: { transform: step.transform } })
    }
  }, [step, navigate])

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">Upload &amp; Mapping</h1>
        <p className="text-sm text-slate-500">
          Upload an export, review the detected platform and mapping, then run the transform.
        </p>
      </div>

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
    </section>
  )
}
