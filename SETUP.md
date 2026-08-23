# Setup & Installation Guide: E-Commerce Sales Transformer

This project is a hybrid desktop-wrapped application consisting of a **Python (FastAPI + Polars/Pandas + SQLite)** backend engine and a **React (Vite + Tailwind CSS)** frontend interface, packaged into a standalone executable with automatic browser launching via **PyInstaller**.

---

## 1. Prerequisites

Ensure the following runtimes are installed on your development machine:
* **Python:** `>= 3.11`
* **Node.js:** `>= 18.x` (LTS recommended) and `npm` / `pnpm`
* **Git**

---

## 2. Directory Structure

```text
ecommerce-data-transformer/
├── AGENTS.md
├── SETUP.md
├── build.py                   # Automated build & packaging script
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI route handlers
│   │   ├── core/              # Config, DB connection, AI client
│   │   ├── modules/
│   │   │   ├── ingestion/     # Spreadsheet reader & delimiter detector
│   │   │   ├── profiler/      # LLM schema mapper & signature cache
│   │   │   ├── transformer/   # Row labeling & cleaning pipeline
│   │   │   ├── storage/       # SQLite models & SQL analytics repository
│   │   │   └── exporter/      # OpenPyXL / XlsxWriter export engine
│   │   └── main.py            # App entrypoint, browser launcher, static mount
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/        # Upload dropzone, mapping modal, data grids
│   │   ├── hooks/             # API mutation & query hooks
│   │   ├── services/          # HTTP API client
│   │   └── App.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
└── docs/
    └── specs/                 # Modular specification markdown files