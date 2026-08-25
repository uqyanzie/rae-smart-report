import { useCallback, useRef, useState } from 'react'
import type { components } from '../services/api'
import { apiClient, ApiError } from '../services/apiClient'

type Ingestion = components['schemas']['IngestionResultDTO']
type Profiler = components['schemas']['ProfilerResponseDTO']
type Transform = components['schemas']['TransformResponseDTO']

export type UploadStep =
  | { kind: 'idle' }
  | { kind: 'uploading'; progress: number }
  | { kind: 'profiling'; ingest: Ingestion; previous?: Profiler }
  | { kind: 'review'; ingest: Ingestion; profile: Profiler }
  | { kind: 'saved'; ingest: Ingestion; profile: Profiler; transform: Transform }

export interface UseUploadFlow {
  step: UploadStep
  error: string | null
  saving: boolean
  upload: (file: File) => void
  reprofile: (ingest: Ingestion, activeSheet: string, previous: Profiler) => void
  runTransform: (payload: components['schemas']['TransformAndSaveRequestDTO']) => void
  reset: () => void
  dismissError: () => void
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    return `${err.code}: ${err.message}`
  }
  return err instanceof Error ? err.message : String(err)
}

export function useUploadFlow(): UseUploadFlow {
  const [step, setStep] = useState<UploadStep>({ kind: 'idle' })
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const requestSeq = useRef(0)

  const runProfile = useCallback((ingest: Ingestion, activeSheet: string, previous?: Profiler) => {
    const requestId = ++requestSeq.current
    setError(null)
    setStep({ kind: 'profiling', ingest, previous })
    apiClient
      .profile({ fileId: ingest.fileId, activeSheet })
      .then((profile) => {
        if (requestId !== requestSeq.current) return
        setStep({ kind: 'review', ingest, profile })
      })
      .catch((err: unknown) => {
        if (requestId !== requestSeq.current) return
        setError(describeError(err))
        setStep(previous ? { kind: 'review', ingest, profile: previous } : { kind: 'idle' })
      })
  }, [])

  const upload = useCallback(
    (file: File) => {
      requestSeq.current += 1
      setError(null)
      setStep({ kind: 'uploading', progress: 0 })
      apiClient
        .uploadFile(file, (progress) => {
          setStep((current) => (current.kind === 'uploading' ? { ...current, progress } : current))
        })
        .then((ingest) => {
          runProfile(ingest, ingest.activeSheet)
        })
        .catch((err: unknown) => {
          setStep({ kind: 'idle' })
          setError(describeError(err))
        })
    },
    [runProfile],
  )

  const reprofile = useCallback(
    (ingest: Ingestion, activeSheet: string, previous: Profiler) => {
      runProfile(ingest, activeSheet, previous)
    },
    [runProfile],
  )

  const runTransform = useCallback((payload: components['schemas']['TransformAndSaveRequestDTO']) => {
    setError(null)
    setSaving(true)
    apiClient
      .transform(payload)
      .then((transform) => {
        setStep((current) =>
          current.kind === 'review' ? { kind: 'saved', ingest: current.ingest, profile: current.profile, transform } : current,
        )
      })
      .catch((err: unknown) => {
        setError(describeError(err))
      })
      .finally(() => setSaving(false))
  }, [])

  const reset = useCallback(() => {
    requestSeq.current += 1
    setStep({ kind: 'idle' })
    setError(null)
    setSaving(false)
  }, [])

  const dismissError = useCallback(() => setError(null), [])

  return { step, error, saving, upload, reprofile, runTransform, reset, dismissError }
}
