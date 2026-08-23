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