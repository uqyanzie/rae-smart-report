# Multi-Phase Backend Implementation Plan: RAE Smart Report Engine

## Objective & Target Architecture

Build a deterministic, production-grade Python backend engine for **RAE Smart Report** that ingests raw sales exports (Shopee and TikTok Shop XLSX/CSV), normalizes variant data across 3 dimensions, executes same-shade fold-back arithmetic, persists atomic records into SQLite with $100\%$ financial precision, generates executive multi-table Excel reports across 4 sheets (`Produk S`, `Produk T`, `Produk 2 S`, `Produk 2 T`) plus per-platform unreported sheets (`Tidak Terlaporkan S` / `Tidak Terlaporkan T`, Phase 7), and exposes REST API endpoints via FastAPI.

### Architecture Overview

```text
backend/
├── app/
│   ├── core/
│   │   ├── config.py              # Application settings & environment resolution
│   │   ├── numeric.py             # Locale-aware (id-ID) currency & quantity sanitizer
│   │   └── security.py            # Path-traversal guards & file sanitization
│   ├── domain/
│   │   ├── catalog.py             # Master product catalog: 7 families, canonical shades,
│   │   │                          # 3 distinct sequences (singles, display, cross),
│   │   │                          # explicit_groups & explicit_bundle_labels (Lipcare & OTG),
│   │   │                          # alias maps, case colors
│   │   └── models.py              # Pure domain models (Family, VariantRecord, GridRow)
│   ├── modules/
│   │   ├── ingestion/
│   │   │   ├── reader.py          # Multi-sheet openpyxl (.xlsx) and csv reader & sniffer
│   │   │   └── exceptions.py      # Structured ingestion errors
│   │   ├── profiler/
│   │   │   ├── adapters.py        # Pinned platform adapters (Shopee ready-to-ship, TikTok)
│   │   │   └── fallback.py        # SHA-256 header signature cache & profiler fallback
│   │   ├── transformer/
│   │   │   ├── normalizer.py      # Token cleaning, alias resolution, prefix stripping
│   │   │   ├── foldback.py        # Same-shade 2-pack fold-back engine (x2 qty, x1 rev, Glow Up Tint scoped)
│   │   │   └── grid.py            # Declarative fixed-grid generator (intra C(n,2)/explicit, cross n x m x 3)
│   │   ├── storage/
│   │   │   ├── database.py        # SQLAlchemy engine, WAL PRAGMA hooks, session factory
│   │   │   ├── models.py          # TransactionItem (BigInteger IDR, case_color) & MappingTemplate
│   │   │   └── repository.py      # Analytics repository executing CTE SQL queries (0-1 unit share)
│   │   └── exporter/
│   │       ├── styles.py          # OpenPyXL palette, font definitions, IDR & 0.00% number formats
│   │       └── report_builder.py  # Dual-table layout generator (Cols A-E / F / G-J) & dynamic formula builder
│   ├── api/
│   │   ├── dtos.py                # Pydantic v2 CamelModel DTOs (wire camelCase bridge, periodStart/End)
│   │   ├── routes.py              # REST API routes (ingest, profile, transform, export)
│   │   └── spa.py                 # Static files & SPA mounting with API routing priority
│   └── main.py                    # Application entrypoint & lifespan
├── tests/
│   ├── conftest.py                # Fixtures, test DB session, sample file paths
│   ├── fixtures/
│   │   └── golden_totals.json     # Extracted oracle totals (22 Shopee + 22 TikTok, Active ratio, addends)
│   ├── test_numeric.py            # 14 table-driven regression tests for id-ID parsing
│   ├── test_domain_catalog.py     # Catalog sequence ordering vs golden oracle as ordered lists + Lipcare structure
│   ├── test_ingestion.py          # Multi-sheet XLSX and CSV parsing against sample_data
│   ├── test_transformer.py        # Label-keyed exact match vs golden_totals.json for Shopee & TikTok
│   ├── test_storage.py            # SQLite PRAGMA, composite indexes, CTE analytics queries
│   ├── test_exporter.py           # In-memory OpenPyXL workbook validation & dynamic formula assertions
│   └── test_api.py                # FastAPI TestClient contract & serialization tests
├── requirements.txt               # Lean runtime & dev dependencies (no Pandas/Polars/xlrd)
└── pyproject.toml                 # Package configuration & pytest configuration
```

---

## Execution Rules & Protocols

1. **The STOP Protocol:** Each execution session MUST work on exactly ONE phase. When a phase is completed and its success criteria are proven, execution STOPS. The next phase MUST be initiated in a fresh session to preserve context hygiene.
2. **Golden-File Scope Boundary:** The target is reproducing the golden report. **Anything the golden workbook does not report is out of scope for report figures** and must never reach a report figure. This covers dash-variant rows (`clean_variant == '-'`) and case colour as a dimension. Verified necessity: including the single non-zero dash row would push golden's Tinted Jelly Balm total from 24 to 25 units and break the match. Full raw-export reconciliation is a separate, later concern.
   - **Phase 7 amendment (DevelopmentFeedback20260826):** non-dash unreported entries — off-grid variant labels (standalone `tidak boleh ecer`, `free gift`, etc.) and non-catalog product groups (Body Toner, Face Toner, Lippie Serum, Blurring Powder, deleted listings) — are **persisted into `transaction_items` with `is_reported = 0`** instead of being excluded. Dash rows remain excluded and are counted in an auditable tally. Persisted unreported volume is reviewable via `GET /api/reports/batches/{id}/unreported` and the `Tidak Terlaporkan S/T` export sheets, but **every report query and the four Produk sheets filter `is_reported = 1`**, so golden totals are byte-identical.
3. **Case Colour Is Not A Dimension:** Tinted Jelly Balm case colours are SKU metadata. Report totals aggregate by shade across all colours. `case_color` is stored for traceability but must never appear in a reporting `GROUP BY`, and must never expand a grid. Verified: golden reports `Bunny Pink` = 15 units spanning four case colours as ONE row, and all 324 case-colour grid rows in the reference workbook are empty scaffolding.
4. **No Deviations:** Code must strictly adhere to the verified domain rules (zero LLM math, declarative grid generation, integer IDR, 0-1 unit share, same-shade fold-back).
5. **Proactive Updates:** If any unforeseen edge case is discovered during execution, stop and discuss before making plan changes.
6. **History Preservation:** Mark completed phases with `[Completed]` and retain all task items.
7. **Proof is Mandatory:** Every phase must culminate in passing automated tests or executable assertions verifying the stated success criteria.
8. **Handoff Brief Maintenance:** At the end of every phase, the `# Handoff Brief` section at the bottom of this document must be updated.

---

## Phase Breakdown

### Phase 0: Setup, Fixtures & Workspace Cleanliness [Completed]
**Goal:** Clean out historical review docs, align `AGENTS.md` and `SETUP.md`, extract golden oracle fixtures, and initialize minimal `requirements.txt` and `pyproject.toml`.

- [x] Remove stale review doc references from `AGENTS.md` (lines 28-31).
- [x] Update `SETUP.md` to reflect the lean stack (FastAPI + OpenPyXL + SQLite + React) and the `domain/` directory structure.
- [x] Extract `backend/tests/fixtures/golden_totals.json` from `sample_data/expected_output/output_13_19_Jul26.xlsx`:
  - 22 Shopee variant totals (`qty`, `revenue`)
  - 22 TikTok variant totals (`qty`, `revenue`)
  - `Active` contribution ratio (`0.05974791292`)
  - Fold-back addends (`Dynamic` revenue addend `139900`, `Energic` qty addend `10`, `Energic` revenue addend `654649`).
- [x] Create/update `backend/requirements.txt` with pinned dependencies: `fastapi`, `uvicorn[standard]`, `pydantic`, `SQLAlchemy`, `openpyxl`, `pytest`, `httpx`. (Explicitly excluding `pandas`, `polars`, and `xlrd`).
- [x] Configure `backend/pyproject.toml` with pytest settings and python path pointing to `backend/`.

**Success Criteria:**
- `pip install -r backend/requirements.txt` completes cleanly.
- `golden_totals.json` exists with verified numeric values extracted from the reference workbook.
- `AGENTS.md` and `SETUP.md` are clean and synchronized.


---

### Phase 1: Core Foundation & Domain Catalog Core (with Lipcare Modeling) [Completed]
**Goal:** Build the bedrock components: locale-safe `id-ID` numeric parsing and the master product catalog supporting 3 distinct sequence orderings and custom multi-group families (Lipcare & Over The Glaze).

- [x] Implement `backend/app/core/numeric.py`:
  - `sanitize_currency(val, decimal_sep=",", default=0.0)` parsing Indonesian format (`.` = thousands, `,` = decimal).
  - Parenthetical negative handling (`(100.000)` $\to -100000$).
  - `sanitize_integer(val)` with half-away-from-zero rounding.
  - `sanitize_percent(val)` returning a $0\text{--}1$ ratio.
- [x] Implement `backend/app/domain/catalog.py`:
  - Immutable `Family` dataclass supporting:
    - `name: str`
    - `shades: Tuple[str, ...]`
    - `singles_order: Tuple[str, ...]`
    - `display_order: Tuple[str, ...]`
    - `cross_order: Tuple[str, ...]`
    - `short_shade: Mapping[str, str]` (e.g. Power Frosted `Kind + Honest` for intra bundles)
    - `explicit_groups: Tuple[Tuple[str, str], ...]` (for Lipcare splitting singles across `Lip Moist`, `Lip Exfoliant`, `Lip Sunscreen`)
    - `explicit_bundle_labels: Tuple[str, ...]` (for Lipcare 7 custom SKUs & OTG 15 literal labels)
    - `aliases: Tuple[str, ...]`
    - `shade_aliases: Mapping[str, str]`
  - The 7 Master Families:
    1. `Glow Up Tint` (11 shades, `Strong` (09) before `Happy` (10) in `display_order`)
    2. `Swipe To Glow` (6 shades)
    3. `Power Frosted Velvet Matte` (short shade `Kind + Honest` for intra bundles, full name for cross)
    4. `Tinted Jelly Balm` (6 shades, 3 case colors)
    5. `The Bloom Perfect Matte Lipstick` (6 shades)
    6. `Over The Glaze` (15 literal `explicit_bundle_labels`)
    7. `Lipcare` (3 shades mapped to 3 distinct report groups + 7 explicit bundle labels: `Lip Exfoliant (2pcs)`, `Lip Exfoliant + Sunscreen`, `Lip Moist (2pcs)`, `Lip Moist + Exfoliant`, `Lip Moist + Exfoliant+ Sunscreen`, `Lip Moist + Sunscreen`, `Lip Sunscreen (2pcs)`)
  - `PRODUK_GROUP_ORDER` (16 group names in emission sequence).
  - `CASE_COLORS` (`Fizzy Pop`, `Sweetie Pop`, `Cherry Pop`).
  - Fast lookup functions: `resolve_shade(token, family=None)`, `resolve_family(token)`.
- [x] Author `backend/tests/test_numeric.py`:
  - 14 table-driven regression tests including `'Rp 50.000'`, `'Rp 100.000'`, `'-Rp 1.000'`, `'(1.000)'`, `'261.911.314'`, `'261.911.314,50'`.
- [x] Author `backend/tests/test_domain_catalog.py`:
  - Assert that `Family.order_for_singles()`, `Family.order_for_pairs()`, and `Family.order_for_cross()` match the expected sequences as **ordered lists**.
  - Assert that Lipcare correctly emits 4 report groups (`Lip Moist`, `Lip Exfoliant`, `Lip Sunscreen`, `Bundling Lipcare`) and exactly 7 explicit bundle labels.

**Success Criteria:**
- `pytest backend/tests/test_numeric.py backend/tests/test_domain_catalog.py` passes with 100% assertions green.
- Zero floating-point or locale parsing discrepancies.

---

### Phase 2: Ingestion & Pinned Platform Adapters [Completed]
**Goal:** Implement resilient multi-sheet spreadsheet ingestion (`.xlsx`, `.csv`) and deterministic column mapping adapters for Shopee and TikTok Shop.

- [x] Implement `backend/app/modules/ingestion/reader.py`:
  - Read `.xlsx` and `.csv` into structured row dictionaries using openpyxl (scoped strictly to `.xlsx` and `.csv`; no `.xls`).
  - Sheet selector with default fallback (e.g. `Produk dengan Performa Terbaik` for Shopee 7-sheet workbook, `Sheet1` for TikTok Shop).
  - CSV delimiter sniffer (supporting `,`, `;`, `\t`).
- [x] Implement `backend/app/modules/profiler/adapters.py`:
  - **Shopee Adapter:** Pinned to `Produk` (B), `Nama Variasi` (E), `SKU Induk` (H), `Produk (Pesanan Siap Dikirim)` (S), `Penjualan (Pesanan Siap Dikirim) (IDR)` (J).
  - **Shopee Parent-Row Pruning:** Drops rows where `Nama Variasi` is `"-"` or empty.
  - **TikTok Shop Adapter:** Pinned to `Produk` (C split on `:` into group and raw_variant), `SKU ID` (A), `Produk terjual` (G), `GMV` (E). No parent rows to prune.
  - Fail loudly with descriptive error if required ready-to-ship columns are missing.
- [x] Implement `backend/app/modules/profiler/fallback.py`:
  - Compute canonical SHA-256 header signatures.
  - Mapping template cache lookup.
- [x] Author `backend/tests/test_ingestion.py`:
  - Ingest `sample_data/raw/raw_shopee_13_19_Jul26.xlsx` and verify exactly 295 parent rows pruned from 1061 total rows (766 child rows). (Verified at implementation: 1061 total rows -> 295 dash rows; 110 of those belong to products WITH child variants and are pruned as true parent summaries, while 185 dash rows are retained as standalone single-variant listings. The adapter therefore returns 951 records = 766 child + 185 standalone; the non-reportable dash rows are excluded at the `persist_batch` boundary and counted in `skipped_unreported`.)
  - Ingest `sample_data/raw/raw_tts_13_19_Jul26.xlsx` and verify 270 rows extracted.

**Success Criteria:**
- `pytest backend/tests/test_ingestion.py` passes.
- Shipped orders correctly extracted; created orders rejected.

---

### Phase 3: Transformation, Normalization & Fixed Grid Generator [Completed]
**Goal:** Implement variant cleaning, 3D case color tagging, same-shade 2-pack fold-back arithmetic (scoped to Glow Up Tint), and combinatorial fixed-grid generation.

- [x] Implement `backend/app/modules/transformer/normalizer.py`:
  - Strip packaging noise (`random keychain`, `tanpa keychain`, `aplikator`).
  - Strip ordinal prefixes (`05. Dynamic` $\to$ `Dynamic`, `01 Peony` $\to$ `Peony`).
  - Split multiple delimiters (`,`, `+`, `/`).
  - Apply alias dictionary (`cheerfull` $\to$ `Cheerful`, `ov hype` $\to$ `Over Hype`, `bunpink` $\to$ `Bunny Pink`).
  - Resolve 3D case colors for Tinted Jelly Balm (`Fizzy Pop`, `Sweetie Pop`, `Cherry Pop`).
  - Surface unmapped tokens explicitly with line context rather than silently dropping revenue.
- [x] Implement `backend/app/modules/transformer/foldback.py`:
  - Detect same-shade intra-family bundles (e.g. `Dynamic, 05. Dynamic`).
  - Scope: Glow Up Tint family (raise error if encountered on other families without verified rule).
  - Apply arithmetic: $1\times$ revenue, $2\times$ quantity added to corresponding single shade.
  - Aggregate duplicate same-shade rows (e.g. duplicate `Gorgeous, 08. Gorgeous`).
  - Raise `ValueError` on multiplicity $N > 2$.
- [x] Implement `backend/app/modules/transformer/grid.py`:
  - `generate_intra_family_grid(family_name)`: emits singles in `order_for_singles()` / `explicit_groups` and pairs in `order_for_pairs()` ($C(n,2)$) / `explicit_bundle_labels`.
  - `generate_cross_family_grid(f1, f2, include_case_colors)`: emits Cartesian pairs ($n \times m$) joining with `", "` and $n \times m \times 3$ joining with `" + "` then `", "`.
  - Normalise all output labels with `.rstrip()`.
- [x] Author `backend/tests/test_transformer.py`:
  - Execute full transformation over raw sample files.
  - Compare results against `backend/tests/fixtures/golden_totals.json` by matching `(variant_label -> qty, revenue)` pairs:
    - 22/22 exact match for TikTok (`Produk T`).
    - 22/22 exact match for Shopee (`Produk S`) verifying fold-back addends (`Dynamic` rev = `6843017 + 139900`, `Energic` qty = `595 + 10`, `Energic` rev = `41678981 + 654649`).

**Success Criteria:**
- `pytest backend/tests/test_transformer.py` passes with 100% exact numerical match against the golden oracle fixture.

---

### Phase 4: SQLite Analytics Storage & CTE Repository [Completed]
**Goal:** Implement transactional SQLite models and analytical CTE queries producing 0-1 unit shares.

- [x] Implement `backend/app/modules/storage/database.py`:
  - SQLite engine configuration with foreign keys, WAL mode, memory temp store.
  - Dialect-guarded connection event hook.
  - Context-managed database session maker.
- [x] Implement `backend/app/modules/storage/models.py`:
  - `TransactionItem`: `id`, `import_batch_id`, `platform`, `period_start`, `period_end`, `product_group`, `raw_variant`, `clean_variant`, `is_bundling`, `is_cross_bundling`, `case_color` (nullable, **SKU traceability only — never in a reporting `GROUP BY`**), `sku`, `qty_sold` (Integer), `revenue` (BigInteger exact IDR), `created_at` (UTC).
  - Note: `transaction_date` (nullable) included for future Phase 2 daily series schema compatibility.
  - Composite indexes: `(import_batch_id, is_cross_bundling, product_group)`, `(platform, period_start, period_end)`, and grid key `(import_batch_id, product_group, clean_variant)`. `case_color` is deliberately **excluded** from the grid key.
  - `MappingTemplate`: cached column mappings and cleaning rules.
- [x] Enforce the golden-file scope boundary (Execution Rule 2) at the persistence boundary:
  - Exclude records where `clean_variant` is `'-'` or empty (180 Shopee records in the reference period; 1 carries Rp 4,950). **Required:** including that row pushes golden's Tinted Jelly Balm total from 24 to 25 units.
  - Exclude products not resolvable to a catalog family (Body Toner, Face Toner, Lippie Serum, Blurring Powder, deleted listings — 17 records, Rp 0 this period).
  - Return an auditable tally (`skipped_unreported`: count, qty, revenue) from the persistence call so excluded volume is reviewable rather than silently vanishing.
- [x] Register Tinted Jelly Balm case-colour tokens as recognised-and-ignorable so the warning channel carries real signal only (`Buttered Yellow`, `Matcha Strawberry`, plus truncations `Fizzy`, `Sweetie`, `Cherry`, `Matcha`, `But Yellow`). Target: Shopee warnings 220 -> ~0, TikTok 15 -> 0.
- [x] Normalize report-key whitespace so the grid left-join keys match persisted data (**required**, discovered post-review):
  - Root cause: `PRODUK_GROUP_ORDER` carries workbook-leftover trailing spaces on `"Swipe To Glow "` and `"Bundling Swipe To Glow "`. `_CANONICAL_GROUP_MAP` in `normalizer.py` propagates them into `product_group` (measured this period: 75 `Swipe To Glow ` + 34 `Bundling Swipe To Glow ` = 109 records) while `grid.py` emits `family.name.rstrip()` clean names and the golden oracle stores clean names too.
  - Fix the source: strip the two entries in `PRODUK_GROUP_ORDER` and update `test_produk_group_order_contains_16_groups` in `test_domain_catalog.py` to assert clean names. Golden-match tests already `.rstrip()` both sides, so they remain green.
  - Defense-in-depth: `.rstrip()` `product_group` and `clean_variant` on both sides of every comparison/join in the repository (rae-report-template skill rule 7: the reference workbook contains 57 manually-entered trailing spaces; do not reproduce them).
  - Not optional: without it, the left-join grid population orphans every Swipe To Glow sale into a group the catalog grid does not contain.
- [x] Implement `backend/app/modules/storage/repository.py`:
  - **Query A (Variant Analytics):** Groups by `(product_group, clean_variant)` — **not** `case_color` — with `contribution_ratio` = `CAST(SUM(qty_sold) AS FLOAT) / total_product_qty` ($0\text{--}1$ ratio).
  - **Query B (Product Group Summary):** Rollup group performance with share against grand total quantity.
  - **Query C (Multi-Platform / Date Range Aggregation).**
  - **Query D (Batch History Overview).**
  - **Query E (Batch Deletion).**
  - **Left-Join Grid Population:** Integrates catalog grid with Query A aggregates, defaulting missing variants to 0 qty and 0 revenue while preserving group presence.
- [x] Author `backend/tests/test_storage.py`:
  - Insert transformed sample data into SQLite test database.
  - Verify Query A returns `Active` contribution ratio `0.05974791292` (matching `golden_totals.json` to 11 decimal places).
  - Verify variant ratios within Glow Up Tint sum to exactly `1.0`.
  - Verify no persisted record has `clean_variant in ('-', '')`.
  - Verify no persisted `product_group` / `clean_variant` carries leading or trailing whitespace, and that the 75 Swipe To Glow singles aggregate under the grid's clean `Swipe To Glow` group (join-key hygiene).
  - Verify Tinted Jelly Balm aggregates to **6 shade rows** (not one per case colour) totalling qty `24`, revenue `2,234,703` — proving case colour does not split rows.
  - Verify the `skipped_unreported` tally reports 180 Shopee exclusions and Rp 4,950.

**Success Criteria:**
- `pytest backend/tests/test_storage.py` passes without float drift or rounding anomalies.
- No reporting query groups by `case_color`; TJB resolves to one row per shade.
- Persisted `product_group` / `clean_variant` keys match the catalog grid exactly (no trailing-whitespace mismatches); Swipe To Glow sales join to the grid's `Swipe To Glow` group.

---

### Phase 5: Executive OpenPyXL Report Exporter [Completed]
**Goal:** Build the dual-table side-by-side Excel builder with native accounting number formatting and dynamically computed formula ranges.

- [x] Implement `backend/app/modules/exporter/styles.py`:
  - Formats: `FORMAT_CURRENCY_IDR`, `FORMAT_PERCENTAGE` (`0.00%`), `FORMAT_INTEGER` (`#,##0`).
  - Slate palette fills (`FILL_HEADER`, `FILL_TOTAL`), typography (`Segoe UI`), thin/double borders.
- [x] Implement `backend/app/modules/exporter/report_builder.py`:
  - Dual-table layout: Left Table (Cols A-E: Variant Breakdown), Col F (Blank 4px separator), Right Table (Cols G-J: Group Summary).
  - **Left Table = sparse.** Emit only variant rows with non-zero quantity (measured survival: `Produk S` 102/181, `Produk T` 92/181, `Produk 2 S` 7/516, `Produk 2 T` 13/840). Note: the 516/840 denominators are reference-workbook measurements; this app's Produk 2 grid is 813 rows across 21 groups (measured this period: `Produk 2 S` 7/813, `Produk 2 T` 13/813).
  - **Right Table = complete.** Always emit every catalog group in `PRODUK_GROUP_ORDER` sequence, even when it contributed no sales, so the group list is stable period-over-period and matches the reference template.
  - **Empty-Group Rule (required):** when a group has **zero** emitted left-table rows, write a literal `0` into Cols H and I instead of a `=SUM(...)` formula. A SUM over an empty/absent range is invalid and would produce a broken reference. This is not a rare edge case — measured fully-zero groups: `Produk S` 1/16, `Produk T` 1/16, **`Produk 2 S` 7/10**, **`Produk 2 T` 7/13** (reference-workbook counts; on this app's 21-group Produk 2 grids the measured fully-zero groups are `Produk 2 S` 18/21 and `Produk 2 T` 15/21).
  - **Contribution Guard:** Col E and Col J divide by a group or grand total. When the divisor is `0`, write a literal `0` rather than a formula, to avoid reproducing the reference workbook's `#DIV/0!` defect.
  - Dynamic formula generation based on actual emitted row indices:
    - Left Table Col E: `=(C{row}/$H${summary_row})*100%` — `summary_row` resolved from the group's real position, never a hardcoded anchor.
    - Right Table Col H: `=SUM(C{start_row}:C{end_row})` (or literal `0` per Empty-Group Rule).
    - Right Table Col I: `=SUM(D{start_row}:D{end_row})` (or literal `0` per Empty-Group Rule).
    - Right Table Col J: `=(H{row}/$H${grand_total_row})*100%` (or literal `0` if grand total is 0).
    - Grand Total: `=SUM(H2:H{last_summary_row})` and `=SUM(I2:I{last_summary_row})`.
  - Auto-fit column dimensions measuring non-formula strings.
  - Multi-sheet workbook builder generating `Produk S`, `Produk T`, `Produk 2 S`, `Produk 2 T`.
- [x] Author `backend/tests/test_exporter.py`:
  - Build workbook in memory from transformed sample datasets.
  - Reload generated bytes with `openpyxl` and assert:
    - Sheet titles match expected 4 sheets.
    - Right-table group count is complete: 16 groups for `Produk S`/`Produk T`, and every catalog cross-group for `Produk 2 S`/`Produk 2 T`.
    - Groups with no emitted variant rows carry literal `0` in H/I and contain **no** `=SUM(` formula.
    - `Bundling Tinted Jelly Balm` (zero in both `Produk S` and `Produk T`) is present with `0`, not omitted.
    - Right-table formulas dynamically reference valid row ranges without out-of-bound anchors.
    - `Produk 2 S` Group 9 is strictly 36 rows without double-counting overrun.
    - No cell contains `#DIV/0!` or a formula dividing by a zero-valued cell.
    - Number formatting masks applied to all numeric cells.

**Success Criteria:**
- `pytest backend/tests/test_exporter.py` passes; workbook structure and dynamic formulas validate cleanly in openpyxl.
- Every summary group from the catalog is present in each sheet; zero-activity groups render `0` rather than being dropped or emitting broken SUM ranges.

---

### Phase 6: FastAPI REST API & Runtime Harness [Completed]
**Goal:** Expose REST endpoints, enforce camelCase JSON serialization, accept period metadata, and configure SPA static mounting with security path guards.

- [x] Implement `backend/app/api/dtos.py`:
  - `CamelModel` base with `alias_generator=to_camel` and `populate_by_name=True`.
  - DTOs: `IngestionResultDTO`, `ColumnMappingDTO`, `TransformAndSaveRequestDTO` (supporting `periodStart` and `periodEnd` from user input), `VariantPerformanceDTO` (including `case_color`), `ProductSummaryDTO`, `BatchSummaryDTO`.
- [x] Implement `backend/app/api/routes.py`:
  - `POST /api/ingest`: Upload spreadsheet, return sheets, headers, sample rows.
  - `POST /api/profile`: Return detected platform adapter or LLM profiler suggestions.
  - `POST /api/transform`: Execute pipeline, store in SQLite, return batch summary.
  - `GET /api/reports/batches`: List historical batches.
  - `GET /api/reports/batches/{id}/variants`: Fetch variant-level breakdown.
  - `GET /api/reports/batches/{id}/products`: Fetch master product group rollups.
  - `DELETE /api/reports/batches/{id}`: Cascade delete batch.
  - `GET /api/export/excel`: Stream generated `.xlsx` with `Content-Disposition`.
- [x] Implement `backend/app/api/spa.py`:
  - Mount `frontend/dist` with `relative_to` path traversal protection and index fallback.
- [x] Implement `backend/app/main.py`:
  - FastAPI application factory, CORS middleware, lifespan events, API router mounting.
- [x] Author `backend/tests/test_api.py`:
  - `TestClient` tests covering the complete upload $\to$ transform $\to$ query $\to$ export flow.
  - Assert that all response JSON keys are strictly `camelCase`.

**Success Criteria:**
- `pytest backend/tests/test_api.py` passes.
- Full end-to-end backend test suite (`pytest backend/tests/`) passes with all tests green.

---

### Phase 7: Persist & Report Unreported Entries [Pending]

**Goal:** Persist non-dash unreported entries — off-grid variants (standalone `tidak boleh ecer`, `free gift`, etc.) and non-catalog product groups — into `transaction_items` with an `is_reported` flag, surface their qty/revenue through the API, and emit per-platform unreported sheets in the exported workbook, **without moving any golden report figure**. Added from `DevelopmentFeedback20260826.md`; runs before the frontend Phase H/I work.

- [ ] Add `is_reported: bool` (default `True`, indexed) to the `TransactionItem` model.
- [ ] Idempotent startup migration in `init_db`: `PRAGMA table_info(transaction_items)` check, then `ALTER TABLE ... ADD COLUMN is_reported BOOLEAN NOT NULL DEFAULT 1` when missing so pre-existing DBs treat stored rows as reported.
- [ ] Rework the `persist_batch` boundary:
  - Dash/empty-variant rows remain excluded and are tallied (`skipped_dash_variant`).
  - On-grid rows persist with `is_reported = True`.
  - Off-grid variants and non-catalog product groups persist with `is_reported = False`.
  - `PersistResult` gains `inserted_reported` / `persisted_unreported` (with off-grid / unresolved sub-tallies); the combined `skipped_unreported` aggregate is retired.
- [ ] Report-boundary guards: Queries A, B, C, D and the grid left-join template add `is_reported = 1` so the Produk workbook, batch `grandTotal*`, the aggregate endpoint, and golden totals stay byte-identical (Shopee 6,910 / Rp 525,973,986; TikTok 11,575 / Rp 658,458,817).
- [ ] New **Query G (unreported breakdown):** per `(product_group, clean_variant, raw_variant)` totals (`total_qty`, `total_revenue`) with `WHERE import_batch_id = :batch_id AND is_reported = 0`.
- [ ] API: `GET /api/reports/batches/{batch_id}/unreported` → `UnreportedVariantDTO[]`; `TransformResponseDTO` gains `unreportedCount` / `unreportedQty` / `unreportedRevenue`; `skipped*` fields are now documented as dash-only.
- [ ] Exporter: `render_unreported_sheet` (single table: `Produk` | `Nama Variasi` | `Raw Variant` | `Produk Terjual` | `Revenue` + TOTAL row, same slate palette and number masks) emitting `Tidak Terlaporkan S` / `Tidak Terlaporkan T` for each platform batch present in the export; the four Produk sheets are untouched.
- [ ] Tests:
  - Rewrite `test_skipped_unreported_tally`: 167 Shopee dash rows still skipped; 13 Shopee unresolved + 1 TikTok off-grid row now **persisted** as unreported.
  - Assert Queries A/B/C/D + aggregate + Produk grid exclude unreported rows (golden figures unchanged).
  - Query G returns the expected unreported rows; export contains the `Tidak Terlaporkan S/T` sheets with the unreported rows and none in Produk sheets.
  - Update the R1 reconciliation invariant: `reported grid qty + unreported persisted qty + dash-skipped qty == raw record qty`.

**Success Criteria:**
- `pytest backend/tests/` passes with all tests green; golden totals unchanged.
- Unreported rows are persisted (never silently dropped), retrievable via the endpoint, present in the `Tidak Terlaporkan S/T` sheets, and absent from the four Produk sheets.

---

## Verification Plan

### Automated Tests
Run the complete backend test suite across all modules:
```powershell
pytest backend/tests/ -v
```

### End-to-End Validation
Execute a full pipeline run against `sample_data/raw/raw_shopee_13_19_Jul26.xlsx` and `sample_data/raw/raw_tts_13_19_Jul26.xlsx`:
1. Ingest both files via API.
2. Verify SQLite row counts and financial totals against `golden_totals.json`.
3. Stream generated Excel workbook and verify that formulas and layouts evaluate accurately.

---

# Handoff Brief

- **Current Phase:** Phase 6 (FastAPI REST API & Runtime Harness) — **completed**, 193/193 tests pass (100% test suite green).
- **What was done:**
  - **Core settings & security modules** `backend/app/core/`:
    - `config.py`: Environment-aware path resolution, settings dataclass (`Settings`), database URL resolution with writable OS path fallback (`%LOCALAPPDATA%/RAESmartReport` on Windows when frozen) ensuring PyInstaller compliance.
    - `security.py`: Path traversal protection (`resolve_within_root`) and filename sanitization (`sanitize_upload_filename`).
  - **REST API contract & DTOs** `backend/app/api/dtos.py`:
    - Reused `CamelModel` base (`alias_generator=to_camel`, `populate_by_name=True`, `from_attributes=True`) across all DTOs for strict wire `camelCase` consistency.
    - Added `IngestionResultDTO`, `ColumnMappingDTO`, `ParentRowRuleDTO`, `CleaningRuleDTO`, `ProfilerResponseDTO`, `ProfileRequestDTO`, `TransformAndSaveRequestDTO` (supporting `periodStart` / `periodEnd` from user input), `VariantPerformanceDTO` (including `case_color`), `ProductSummaryDTO`, `BatchSummaryDTO`, `TransformResponseDTO`, `DeleteBatchResponseDTO`.
  - **REST routes** `backend/app/api/routes.py`:
    - Ingestion endpoint `POST /api/ingest` with multi-sheet metadata inspection and in-memory upload store.
    - Profiling endpoint `POST /api/profile` supporting automatic adapter detection and SHA-256 header signature template caching.
    - Transformation endpoint `POST /api/transform` running the deterministic ELT pipeline, template saving, and SQLite persistence.
    - Report querying endpoints: `GET /api/reports/batches`, `GET /api/reports/batches/{id}/variants`, `GET /api/reports/batches/{id}/products`, and idempotent `DELETE /api/reports/batches/{id}`.
    - Streaming Excel export `GET /api/export/excel` accepting batch IDs and generating multi-sheet workbooks (`Produk S`, `Produk T`, `Produk 2 S`, `Produk 2 T`).
  - **SPA & Error handling**:
    - `spa.py`: Static file mounting with index fallback and path traversal guards (graceful API-only mode when `frontend/dist` is not yet built).
    - `errors.py`: Canonical error envelope `{status, code, message, details}` and centralized exception handlers for `IngestionError`, `HTTPException`, and `RequestValidationError`.
    - `main.py`: Application factory `create_app()` with lifespan context manager for lazy DB engine initialization and CORS middleware.
  - **End-to-end API tests** `backend/tests/test_api.py` (14 tests):
    - Validated full lifecycle: upload $\to$ profile $\to$ transform $\to$ query variants/products $\to$ stream Excel workbook $\to$ delete batch.
    - Verified strict `camelCase` serialization across all response payloads with recursive assertions.
    - Validated exact matching of golden report numbers (Shopee 6,910 / Rp 525,973,986; TikTok 11,575 / Rp 658,458,817).
  - **Full Backend Suite:** 193 passed in ~11.2s across all 8 test modules (`test_numeric.py`, `test_domain_catalog.py`, `test_ingestion.py`, `test_transformer.py`, `test_storage.py`, `test_exporter.py`, `test_api.py`, `test_fixtures.py`).
- **What is next:** 
  - **Phase 7 (Persist & Report Unreported Entries)** — added from `DevelopmentFeedback20260826.md`: persist non-dash unreported entries (`tidak boleh ecer`, `free gift`, off-grid variants, non-catalog products) into `transaction_items` with `is_reported = 0`, guard every report query with `is_reported = 1`, add `GET /api/reports/batches/{id}/unreported`, and emit `Tidak Terlaporkan S/T` export sheets.
  - After Phase 7: frontend **Phase H (Unreported Entries display)** then **Phase I (Integration & Packaging)** per `FrontendDevelopmentPlan.md`.
- **Artifacts:**
  - Plan: [BackendImplementationPlan.md](BackendImplementationPlan.md)
  - Skill references: `.agents/skills/fullstack-bridge-contract/`, `.agents/skills/pyinstaller-packaging-guardian/`, `.agents/skills/rae-report-template/SKILL.md`


