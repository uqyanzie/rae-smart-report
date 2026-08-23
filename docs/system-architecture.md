# Module Specification: System Architecture & Tech Stack

## 1. System Architecture Diagram
+─────────────────────────────────────────────────────────────────────────+
|                        PRESENTATION LAYER (UI)                          |
|  - File Upload Zone (Drag-and-Drop XLSX / CSV)                          |
|  - AI Mapping Review & Rule Adjuster Modal                              |
|  - SQL-Powered Data Grid & Performance Analytics (Recharts)             |
|  - Export Trigger (.xlsx with native accounting formatting)             |
+────────────────────────────────────┬────────────────────────────────────+
│ (IPC / HTTP Client)
+────────────────────────────────────v────────────────────────────────────+
|                      APPLICATION / SERVICE LAYER                        |
|                                                                         |
|  ┌─────────────────────┐   Hash Miss   ┌─────────────────────────────┐  |
|  │  Ingestion Service  ├──────────────►│    AI Schema Profiler       │  |
|  │  (Parse, Delimit)   │               │ (LLM Structured Outputs API)│  |
|  └──────────┬──────────┘               └──────────────┬──────────────┘  |
|             │                                         │                 |
|             │ Cached / Verified Mapping               │ Saved Template  |
|             ▼                                         │                 |
|  ┌────────────────────────────────────────┐           │                 |
|  │      Row Labeling Transformer          │◄──────────┘                 |
|  │   - Filter aggregate parent rows       │                             |
|  │   - Clean variant strings via Regex    │                             |
|  │   - Tag isBundling and productGroup    │                             |
|  └──────────────────┬─────────────────────┘                             |
+─────────────────────┼───────────────────────────────────────────────────+
│ Batch Insert / SQL Queries
+─────────────────────v───────────────────────────────────────────────────+
|                        PERSISTENCE LAYER (DB)                           |
|                      SQLite Engine (app_data.db)                        |
|  - transaction_items: Labeled granular transaction records              |
|  - mapping_templates: Signature cache for deterministic re-use          |
+─────────────────────────────────────────────────────────────────────────+

## 2. Recommended Tech Stack
- **Framework:** Next.js (App Router) / Vite + Express / FastAPI.
- **Languages:** TypeScript / Node.js or Python 3.11+.
- **Database:** SQLite via Prisma ORM / Drizzle ORM / SQLAlchemy.
- **Spreadsheet Generation:** `exceljs` (Node.js) or `openpyxl` / `xlsxwriter` (Python).