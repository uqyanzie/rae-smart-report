# Module Specification: System Architecture & Tech Stack

## 1. System Architecture Diagram

```text
+─────────────────────────────────────────────────────────────────────────+
|                        PRESENTATION LAYER (UI)                          |
|  - File Upload Zone (Drag-and-Drop XLSX / CSV)                          |
|  - Platform & Batch Selector (Shopee, TikTok Shop, Tokopedia, Lazada)   |
|  - AI Mapping Review & Rule Verification Modal (Fallback for unknown)   |
|  - SQL-Powered Dual-Table Data Grid (Recharts & Virtualized Table)      |
|  - Multi-Sheet Excel Export Trigger (.xlsx with OpenPyXL formatting)    |
+────────────────────────────────────┬────────────────────────────────────+
                                     │ (IPC / HTTP Client - JSON camelCase)
+────────────────────────────────────v────────────────────────────────────+
|                      APPLICATION / SERVICE LAYER                        |
|                                                                         |
|  ┌─────────────────────┐   Unknown Format  ┌─────────────────────────┐  |
|  │  Ingestion Service  ├──────────────────►│   AI Schema Profiler    │  |
|  │ (Multi-Sheet Select,│                   │(LLM Structured Fallback)│  |
|  │  id-ID Num Parsing) │                   └────────────┬────────────┘  |
|  └──────────┬──────────┘                                │               |
|             │                                           │ User-Verified |
|             │ Pinned Adapter / Cached Signature         │ Template      |
|             ▼                                           │               |
|  ┌────────────────────────────────────────┐             │               |
|  │       Row Labeling Transformer         │◄────────────┘               |
|  │   - Deterministic Parent Row Pruning   │                             |
|  │   - Ordinal & Gimmick Regex Cleaning   │                             |
|  │   - Same-Shade 2-Pack Fold-Back Engine │                             |
|  │   - Intra / Cross-Family Route Tagging │                             |
|  └──────────────────┬─────────────────────┘                             |
|                     │                                                   |
|                     │ Atomic Batch Inserts                              |
|                     ▼                                                   |
|  ┌────────────────────────────────────────┐    Populates Fixed Grid     |
|  │         Master Product Catalog         │─────────────────────────┐   |
|  │   - Authoritative Shade & Group Map    │                         │   |
|  │   - C(n,2) & Cross-Family Grid Gen     │                         │   |
|  └────────────────────────────────────────┘                         │   |
+─────────────────────┼───────────────────────────────────────────────┼───+
                      │ Batch Insert / SQL Aggregations               │
+─────────────────────v───────────────────────────────────────────────v───+
|                        PERSISTENCE LAYER (DB)                           |
|                      SQLite Engine (app_data.db)                        |
|  - transaction_items: Atomic labeled granular transaction records (with `is_reported` flag separating report-grid rows from persisted non-dash unreported entries)       |
|  - mapping_templates: SHA-256 header signature cache                    |
+─────────────────────────────────────────────────────────────────────────+
```

---

## 2. Authoritative Tech Stack

| Component | Selected Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Engine** | **Python 3.11+ / FastAPI** | High performance, native async, Pydantic type validation, robust data processing libraries. |
| **Database & ORM** | **SQLite 3 + SQLAlchemy** | Local embedded zero-config storage, ACID transactions, atomic aggregation queries. |
| **Spreadsheet Engine** | **OpenPyXL** | Native Excel formula rendering, custom number formatting (IDR Accounting, Percentage), dual-table layout generation. |
| **Frontend UI** | **React 18+ (Vite + TypeScript)** | Fast HMR, strong typing matching Pydantic DTOs, reactive state management. |
| **Styling** | **Tailwind CSS** | Clean modern slate design system, responsive layouts, dark/light themes. |
| **Desktop Packaging** | **PyInstaller** | Bundles FastAPI backend, React SPA static assets, and SQLite runner into a standalone local `.exe`. |

> [!NOTE]
> **Phase 8 (Lazada):** The Lazada adapter resolves each `Seller SKU` against `sku_mapping.csv` (`Kode Variasi` column), shipped as `backend/app/data/sku_mapping.json`. Lazada exports a single `Produk` sheet with 5 preamble rows before the header; the reader skips leading sparse rows so header detection stays deterministic. Exports render `Produk Laz` / `Tidak Terlaporkan Laz` (no `Produk 2 Laz`).