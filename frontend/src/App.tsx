import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { UploadModalProvider, useUploadModal } from './context/UploadModalContext'
import BatchDetailPage from './pages/BatchDetailPage'
import BatchesPage from './pages/BatchesPage'
import ExportPage from './pages/ExportPage'
import HomePage from './pages/HomePage'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/batches', label: 'Batches' },
  { to: '/export', label: 'Export' },
]

function navClass({ isActive }: { isActive: boolean }): string {
  return `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-700 hover:text-white'
  }`
}

function HeaderBar() {
  const { openUploadModal } = useUploadModal()

  return (
    <header className="bg-slate-800 shadow sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="text-sm font-bold tracking-wide text-white flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-indigo-500" />
            RAESmartReport
          </span>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <button
          type="button"
          onClick={openUploadModal}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3.5 py-1.5 text-sm font-semibold text-white shadow-xs hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 focus:ring-offset-slate-800 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span>Upload Export</span>
        </button>
      </div>
    </header>
  )
}

function App() {
  return (
    <UploadModalProvider>
      <div className="flex min-h-screen flex-col bg-slate-100 font-sans text-slate-800 antialiased">
        <HeaderBar />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<Navigate to="/" replace />} />
            <Route path="/batches" element={<BatchesPage />} />
            <Route path="/batches/:batchId" element={<BatchDetailPage />} />
            <Route path="/export" element={<ExportPage />} />
          </Routes>
        </main>
      </div>
    </UploadModalProvider>
  )
}

export default App

