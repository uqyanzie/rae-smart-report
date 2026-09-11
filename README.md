# RAE Smart Report

Deterministic E-Commerce Sales Transformer. Ingests raw sales exports (CSV/XLSX)
from Shopee, TikTok Shop, Tokopedia, and Lazada, labels them into atomic row-level
records, stores them in SQLite, and generates aggregated multi-table reports and
formatted Excel downloads via SQL queries.

The project is a desktop-style local application: a **Python (FastAPI + SQLAlchemy
+ SQLite + OpenPyXL)** backend serving a **React (Vite + TypeScript + Tailwind)**
SPA, packaged into a single standalone `.exe` with PyInstaller.

- Architecture and data flow: `docs/system-architecture.md`
- Module specifications: `docs/specs/`
- Packaging and distribution notes: `SETUP.md`

---

## 1. Prerequisites

| Tool | Version | Notes |
| :--- | :--- | :--- |
| Python | `>= 3.11` | Add to `PATH`; verify with `python --version` |
| Node.js | `>= 18` (LTS) | Includes `npm`; verify with `node --version` |
| Git | any recent | To clone the repository |

All development commands below are written for **Windows PowerShell**. On macOS /
Linux, replace `python` with `python3` and use `source .venv/bin/activate` instead
of the Windows activation script.

---

## 2. Clone and Enter the Repository

```powershell
git clone <repository-url> rae-smart-report
Set-Location rae-smart-report
```

All commands in this guide assume the repository root as the working directory.

---

## 3. Backend Setup

Create and activate a virtual environment, then install the runtime and dev
dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

`backend/requirements.txt` includes the core runtime (`fastapi`, `uvicorn`,
`pydantic`, `SQLAlchemy`, `openpyxl`, `pystray`, `Pillow`) plus dev/test tooling
(`pytest`, `httpx`). For the PyInstaller build, also install:

```powershell
python -m pip install pyinstaller
```

If PowerShell blocks the activation script, allow script execution for the
current session first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 4. Frontend Setup

Install the Node dependencies:

```powershell
npm install --prefix frontend
```

---

## 5. Run in Development

Run the backend and frontend in **two separate terminals** (both with the venv
active in the backend terminal).

### Terminal 1 — Backend API

```powershell
Set-Location backend
python -m uvicorn app.main:app --reload --port 8000
```

- API root: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

The database is created automatically as `rae_smart_report.db` in the backend
working directory (see [Configuration](#8-configuration) to override it).

### Terminal 2 — Frontend SPA (hot reload)

```powershell
npm run dev --prefix frontend
```

Open the Vite dev server URL (default `http://127.0.0.1:5173`). Vite proxies all
`/api/*` requests to the backend on port `8000`, so no CORS setup is needed.

### Single-process alternative

To serve the pre-built SPA from the backend itself instead of Vite:

```powershell
npm run build --prefix frontend      # emits frontend/dist
python backend\run.py                # serves API + SPA on http://127.0.0.1:8000
```

`backend\run.py` also opens the default browser. In a plain (non-frozen) dev run
the system-tray icon is disabled by default.

---

## 6. Run the Tests

Backend tests use `pytest`; configuration lives in `backend/pyproject.toml`.

```powershell
python -m pytest backend
```

Frontend type-checking and linting:

```powershell
npm run typecheck --prefix frontend
npm run lint --prefix frontend
```

Repository-wide Python linting uses `ruff` (config in `pyproject.toml`):

```powershell
ruff check .
```

---

## 7. Build the Distribution

Build the standalone desktop executable (bundles the backend, the built SPA, and
the SKU-mapping artifact):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

This runs the Vite production build in `frontend\`, then packages
`backend\run.py` with `packaging.spec` via PyInstaller. The result is
`dist\RAE-Smart-Report.exe`.

Verify the packaged build end-to-end against the golden sample files:

```powershell
python scripts\smoke_test.py            # ingest -> transform -> unreported -> export
python scripts\smoke_test.py --tray     # same, via the system-tray startup path
python scripts\smoke_test.py --idle-exit  # verifies the idle auto-shutdown
```

At runtime the executable:

- serves the SPA at `http://127.0.0.1:8000` (override with `RAE_PORT` / `RAE_HOST`),
- opens the default browser once `/api/health` responds (disable with `RAE_SKIP_BROWSER=1`),
- shows a system-tray icon with **Open Dashboard** / **Exit** (disable with `RAE_TRAY=0`),
- auto-exits once no browser client has been seen for `RAE_IDLE_SHUTDOWN_SECONDS`
  (default `180`; set `0` to keep running in the tray until Exit),
- persists SQLite to `%LOCALAPPDATA%\RAESmartReport\app_data.db`,
- writes runtime logs to `%LOCALAPPDATA%\RAESmartReport\rae_smart_report.log`.

---

## 8. Configuration

All environment variables are optional.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `RAE_HOST` | `127.0.0.1` | Server bind host |
| `RAE_PORT` | `8000` | Server bind port |
| `RAE_DATABASE_URL` | dev: `sqlite:///rae_smart_report.db` | SQLAlchemy database URL |
| `RAE_FRONTEND_DIST` | repo `frontend\dist` (or bundled `_MEIPASS`) | Built SPA directory |
| `RAE_SKU_MAPPING` | repo `backend\app\data\sku_mapping.json` | Lazada SKU-mapping artifact |
| `RAE_SKIP_BROWSER` | unset | `1` to prevent auto-opening the browser |
| `RAE_TRAY` | frozen builds only | `1`/`0` to force tray on/off |
| `RAE_IDLE_SHUTDOWN_SECONDS` | `180` | Idle grace period before auto-exit; `0` disables |

---

## 9. Project Layout

```text
rae-smart-report/
├── AGENTS.md                     # Project conventions and agent skills
├── README.md                     # This setup guide
├── SETUP.md                      # Packaging & distribution guide
├── pyproject.toml                # Ruff configuration
├── packaging.spec                # PyInstaller build spec
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI routes, DTOs, SPA mount
│   │   ├── core/                 # Config, lifecycle, tray, sanitizers
│   │   ├── domain/               # Master product catalog & models
│   │   ├── modules/
│   │   │   ├── ingestion/        # Spreadsheet reader & CSV sniffer
│   │   │   ├── profiler/         # Platform adapters & header cache
│   │   │   ├── transformer/      # Normalization & grid generation
│   │   │   ├── storage/          # SQLite models & analytics repository
│   │   │   └── exporter/         # OpenPyXL export engine
│   │   ├── data/sku_mapping.json # Lazada SKU-mapping artifact
│   │   └── main.py               # FastAPI app factory
│   ├── run.py                    # Runtime/PyInstaller entrypoint
│   ├── requirements.txt
│   └── tests/                    # pytest regression & golden-oracle suites
├── frontend/                     # Vite + React + TypeScript SPA
├── sample_data/                  # Raw exports & golden reference workbooks
├── scripts/                      # build.ps1, smoke_test.py
└── docs/                         # Architecture & module specifications
```

---

## 10. Troubleshooting

- **`Activate.ps1` cannot be loaded** — run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then re-activate.
- **`uvicorn` cannot import `app`** — start it from the `backend\` directory (or
  ensure `backend` is on `PYTHONPATH`).
- **Frontend shows 404s on `/api/*`** — confirm the backend is running on port
  `8000`, matching the Vite proxy target in `frontend\vite.config.ts`.
- **PyInstaller build fails inside `build\`/`dist\`** — pass `--noconfirm --clean`
  (as `scripts\build.ps1` does) to clear stale artifacts.
