# Setup & Installation Guide: E-Commerce Sales Transformer

This project is a desktop application consisting of a **Python (FastAPI + OpenPyXL + SQLite)** backend engine and a **React (Vite + Tailwind CSS)** frontend interface, packaged into a standalone executable with automatic browser launching via **PyInstaller**.

---

## 1. Prerequisites

Ensure the following runtimes are installed on your development machine:
* **Python:** `>= 3.11`
* **Node.js:** `>= 18.x` (LTS recommended) and `npm` / `pnpm`
* **Git**

---

## 2. Directory Structure

```text
rae-smart-report/
├── AGENTS.md
├── SETUP.md
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI route handlers & DTOs
│   │   ├── core/              # Config, numeric sanitizer & security
│   │   ├── domain/            # Master product catalog & pure domain models
│   │   ├── modules/
│   │   │   ├── ingestion/     # Multi-sheet spreadsheet reader & CSV delimiter sniffer
│   │   │   ├── profiler/      # Pinned platform adapters & header cache
│   │   │   ├── transformer/   # Normalization, fold-back & fixed grid generator
│   │   │   ├── storage/       # SQLite models & CTE analytics repository
│   │   │   └── exporter/      # Executive OpenPyXL export engine
│   │   └── main.py            # App entrypoint, lifespan & SPA static mount
│   ├── tests/
│   │   ├── fixtures/          # Golden oracle benchmarks & extraction scripts
│   │   └── ...                # Modular regression test suites
│   ├── requirements.txt       # Lean runtime & dev dependencies
│   └── pyproject.toml         # Package and pytest configuration
├── frontend/
│   ├── src/
│   │   ├── components/        # Upload dropzone, mapping modal, data grids
│   │   ├── hooks/             # API mutation & query hooks
│   │   ├── services/          # HTTP API client
│   │   └── App.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── sample_data/
│   ├── expected_output/       # Golden reference workbooks
│   └── raw/                   # Raw platform sales exports
└── docs/
    ├── plan/                  # Implementation plans & tracking
    └── specs/                 # Modular specification markdown files
```

---

## 3. Packaging & Distribution

Build the standalone desktop executable (bundles the backend, the built SPA, and
the Lazada SKU-mapping artifact):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

This runs the Vite production build in `frontend/`, then packages
`backend/run.py` with `packaging.spec` via PyInstaller. The result is
`dist/RAE-Smart-Report.exe` (~20 MB, one file, hidden console).

At runtime the executable:

- serves the SPA at `http://127.0.0.1:8000` (override with `RAE_PORT` / `RAE_HOST`),
- opens the default browser automatically once `/api/health` responds (disable with `RAE_SKIP_BROWSER=1`),
- shows a system-tray icon with **Open Dashboard** / **Exit** (disable with `RAE_TRAY=0`),
- auto-exits cleanly once no browser client has been seen for `RAE_IDLE_SHUTDOWN_SECONDS`
  (default `180`; set `0` to keep running in the tray until Exit), so simply closing
  the dashboard tab shuts the app down,
- persists SQLite to `%LOCALAPPDATA%\RAESmartReport\app_data.db` (never into the read-only `sys._MEIPASS`),
- writes runtime logs to `%LOCALAPPDATA%\RAESmartReport\rae_smart_report.log`.

Verify a packaged build end-to-end against the golden sample files:

```powershell
python scripts/smoke_test.py                      # full ingest -> transform -> unreported -> export
python scripts/smoke_test.py --tray               # same, via the system-tray startup path
python scripts/smoke_test.py --idle-exit          # verifies the idle auto-shutdown
```