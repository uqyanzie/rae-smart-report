import { NavLink, Route, Routes } from 'react-router-dom'
import BatchesPage from './pages/BatchesPage'
import ExportPage from './pages/ExportPage'
import HomePage from './pages/HomePage'
import UploadPage from './pages/UploadPage'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/upload', label: 'Upload' },
  { to: '/batches', label: 'Batches' },
  { to: '/export', label: 'Export' },
]

function navClass({ isActive }: { isActive: boolean }): string {
  return `rounded-md px-3 py-1.5 text-sm font-medium ${
    isActive ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-700 hover:text-white'
  }`
}

function App() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <header className="bg-slate-800 shadow">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <span className="text-sm font-semibold tracking-wide text-white">RAESmartReport</span>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/batches" element={<BatchesPage />} />
          <Route path="/export" element={<ExportPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
