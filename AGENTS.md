# AGENTS.md - E-Commerce Sales Transformer

## Project Overview
A web-based local application that ingests raw sales exports (CSV/XLSX) from various e-commerce platforms, labels and normalizes them into atomic row-level records, stores them in SQLite, and generates aggregated multi-table reports and formatted Excel downloads via SQL queries.

## Architecture Philosophy: ELT (Extract -> Label/Load -> Query)
1. **Raw File Ingestion:** Parse raw spreadsheet.
2. **AI Schema Mapping & Pruning:** AI maps columns and provides string normalization rules. Filter out parent/summary rows (e.g. `"-"` variant rows).
3. **Persistence:** Insert labeled, clean records directly into `transaction_items`.
4. **On-Demand Reporting:** UI views, charts, and Excel exports must be derived dynamically using SQLite SQL queries (`SUM`, `GROUP BY`, `JOIN`, Window functions).

## Core Directives & Boundaries
1. **Zero LLM Calculations:** Never ask the AI model to calculate metrics or sums. Use SQLite aggregation queries for 100% precision.
2. **Avoid Pre-computed Redundant Tables:** Do not create static aggregate tables for reports. Rely on SQL aggregation from `transaction_items` to ensure flexible filtering (by batch, date range, or platform).
3. **Deterministic Parent-Row Elimination:** Prune subtotal/header rows before inserting into `transaction_items` to prevent double-counting.
4. **Relative Path Documentation Rule:** All documentation, skill definitions, and specification files must strictly use relative path referencing to preserve portability and cleanliness across environments.

## Standard Modular References
All specifications are structured in `docs/`:
- `docs/specs/file-ingestion-parser.md`
- `docs/specs/ai-schema-profiler.md`
- `docs/specs/row-labeling-transformer.md`
- `docs/specs/storage-analytics-engine.md`
- `docs/specs/excel-exporter-engine.md`
- `docs/system-architecture.md`

## Implementation Plan Reference
The execution plan and architecture specifications are documented in:
- `docs/plan/ImplementationPlan.md`
- `docs/system-architecture.md`
- `docs/specs/`

## Active Agent Skills & Capabilities
- `@data-engineering-deterministic`: Enforces zero-LLM math, exact regex variant extraction, and parent-row pruning.
- `@llm-structured-profiler`: Handles Pydantic structured output validation and header signature hashing.
- `@sqlite-analytics-specialist`: Maintains transactional SQLite schema and writes analytics CTE queries.
- `@pyinstaller-packaging-guardian`: Ensures path safety (`sys._MEIPASS`) and writable DB paths for `.exe` bundles.
- `@excel-styling-formatter`: Applies accounting number formatting and dual-table layouts in OpenPyXL.
- `@fullstack-bridge-contract`: Synchronizes FastAPI Pydantic schemas with React TypeScript interfaces.
- `@rae-report-template`: Manages master product catalog, 3D combinatorial fixed grids, shade alias resolution, and same-shade fold-back rules.