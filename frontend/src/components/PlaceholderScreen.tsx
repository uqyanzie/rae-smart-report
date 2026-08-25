interface PlaceholderScreenProps {
  phase: string
  title: string
  description: string
}

export default function PlaceholderScreen({ phase, title, description }: PlaceholderScreenProps) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-12 text-center">
      <span className="mb-3 rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
        {phase}
      </span>
      <h2 className="text-xl font-semibold text-slate-800">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-slate-500">{description}</p>
    </div>
  )
}
