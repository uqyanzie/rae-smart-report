# Multi-Phase Development Plan: Contract Reconciliation + Frontend SPA

## Objective

Complete the remaining backend contract work identified in `BackendRemediationBrief.md`, then build the React + TypeScript frontend SPA that consumes the FastAPI REST API. The backend ELT engine (Phases 0–6 of `BackendImplementationPlan.md`) is complete and sealed; this plan governs the handoff phase and the frontend build.

## Current State (entering Phase A)

- Backend: 205/205 tests green, `ruff` clean, golden workbook match preserved.
- Backend API is functionally complete for the single-batch flow (ingest → profile → transform → view → export → delete).
- Frontend: `frontend/` does not exist yet. `SETUP.md` prescribes Vite + React + TS + Tailwind with `components/`, `hooks/`, `services/` structure.
- The bridge skill reference `api_endpoints.md` has been reconciled with the real `routes.py` (Phase A1, done during planning).

## Execution Rules & Protocols

1. **The STOP Protocol:** Each execution session works on exactly ONE phase. When a phase's success criteria are proven, execution stops and the next phase starts in a fresh session.
2. **Contract-First:** The OpenAPI spec at `/openapi.json` is the canonical client contract. The TypeScript client is generated from it; hand-maintained DTOs must match the generated output. The `@fullstack-bridge-contract` skill governs all wire conventions.
3. **camelCase on the wire:** JSON bodies serialize `camelCase` via `CamelModel`. The `is_cross_bundling` query parameter is deliberately `snake_case` (bound to the FastAPI parameter name) and must not be "fixed" by renaming the endpoint — a generated client already names it correctly.
4. **Golden-File Boundary:** Workbook totals must stay fixed at Shopee 6,910 / Rp 525,973,986 and TikTok 11,575 / Rp 658,458,817. Any backend change that moves a golden total has crossed the Execution Rule 2 boundary.
5. **Relative Paths:** All documentation references use relative paths (no absolute filesystem paths).
6. **Proof is Mandatory:** Every phase ends with passing tests or executable assertions for its stated success criteria.
7. **Handoff Brief Maintenance:** At the end of every phase, the `# Handoff Brief` section at the bottom of this document must be updated.

---

## 2026-08-25 Scope Extension (DevelopmentFeedback20260825.md)

New feedback supersedes parts of the earlier plan. Disposition of the three items:

1. **Exported Excel golden display — new Phase F.** The exported workbook must reproduce the golden file's data display: the full catalog grid on the left table (every product group + every variant), with unsold variants' qty/revenue cells rendered per the golden (blank, with unguarded `=(C{r}/$H${group})*100%` contribution formulas that evaluate to `#DIV/0!` on zero-total groups). This intentionally reverses the earlier "sparse left table" and "never reproduce `#DIV/0!`" guidance **for the export display only** (user-confirmed).
2. **Batch-scoped dashboard — new Phase G.** `HomePage` becomes a batch-selector dashboard with a Contribution pie chart, a Product sales bar chart, and a data list filtered by 3 multi-select checkboxes (Single / Bundling / Cross Bundling), backed by a new optional `isBundling` filter on `/api/reports/batches/{id}/variants` and `/api/reports/batches/{id}/products`.

The former **Phase F (Integration & Packaging)** is renamed **Phase H** and now runs after the new feature phases; the STOP protocol applies unchanged (one phase per session).

---

## Phase A: Backend Contract Reconciliation & Completion [Complete]

**Goal:** Eliminate the remaining contract gaps so the frontend never has to chase a moving API.

- [x] **A1 — Reconcile `api_endpoints.md`** (`backend/app/api/routes.py` vs `.agents/skills/fullstack-bridge-contract/references/api_endpoints.md`):
  - Correct the endpoint catalog to the real routes (`/api/ingest`, `/api/profile`, `/api/transform`, `/api/reports/batches`, `/api/reports/batches/{id}/variants`, `/api/reports/batches/{id}/products`, `/api/export/excel`, `DELETE /api/reports/batches/{id}`).
  - Document the error envelope (`details` omitted when null), error codes, the exactly-one-batch-per-platform export constraint, and the transform `reported*` vs batch-list `grandTotal*` semantics.
  - Add the planned `GET /api/reports/aggregate` endpoint.
- [x] **A2 — Map the same-shade N>2 fold-back violation to a 4xx error:**
  - Introduce a dedicated exception (e.g. `InvalidVariantError`) in `backend/app/modules/transformer/`; the normalizer's multiplicity guard raises it instead of a bare `ValueError`.
  - Register a handler in `backend/app/api/errors.py` mapping it to `422 INVALID_VARIANT`, carrying the offending shade, raw variant, and SKU in the message.
  - Tests: `backend/tests/test_transformer.py` asserts the new exception type; `backend/tests/test_api.py` uploads a CSV containing a 3-pack row and asserts HTTP 422 with `code == "INVALID_VARIANT"` and that no partial batch was persisted.
- [x] **A3 — Expose Query C as `GET /api/reports/aggregate`:**
  - New `AggregateRowDTO` (`platform`, `productGroup`, `cleanVariant`, `totalQty`, `totalRevenue`, `contributionRatio`) in `backend/app/api/dtos.py`.
  - Route in `backend/app/api/routes.py` with optional camelCase query params `platform`, `periodStart`, `periodEnd`, `isCrossBundling`, delegating to `AnalyticsRepository.multi_platform_aggregation` (R9 bound coercion already in place).
  - Mirror the DTO in `.agents/skills/fullstack-bridge-contract/references/frontend_dtos.ts` and update `api_endpoints.md` to move the endpoint from Planned to active.
  - Tests: `backend/tests/test_api.py` end-to-end coverage (platform filter, date range inclusion, cross-bundling toggle).
- [x] **A4 — OpenAPI contract check:**
  - Assert every `/openapi.json` response field is `camelCase` and matches `frontend_dtos.ts` (especially the R5 `reported*` fields).
  - Verify `openapi-typescript` can generate `src/services/api.ts` from `/openapi.json` with zero manual edits.

**Success Criteria:**
- Full backend suite green (`pytest backend/tests/`), `ruff` clean, golden totals unchanged.
- A 3-pack upload returns 422 `INVALID_VARIANT` (never 500), no partial batch persisted.
- `GET /api/reports/aggregate` returns correct filtered rows for both sample batches.
- `/openapi.json` type-generates a client with no manual edits.

---

## Phase B: Frontend Scaffolding [Complete]

**Goal:** Stand up the SPA skeleton and the generated API client so all subsequent phases build on a stable contract.

- [x] Scaffold Vite + React + TypeScript + Tailwind v4 in `frontend/` matching the `SETUP.md` layout (`src/components/`, `src/hooks/`, `src/services/`, `App.tsx`).
- [x] Add `openapi-typescript` codegen: `npm run generate:api` emits `src/services/api.ts` from the backend `/openapi.json`; commit the generated file so the build does not require a running backend.
- [x] Thin API service wrapper (`src/services/apiClient.ts`): typed fetch calls, base URL resolution (Vite dev proxy `/api` → uvicorn), and shared handling for the `{ status, code, message, details? }` error envelope.
- [x] Application shell: routing, layout, and empty screen placeholders for each feature phase.
- [x] Wire `frontend/dist` build output to the existing SPA mount in `backend/app/api/spa.py` (API-only fallback already supported).

**Success Criteria:**
- `npm run dev` boots Vite; proxied `/api/reports/batches` returns data from the live backend.
- `npm run generate:api && npm run typecheck` pass cleanly.
- `npm run build` produces `frontend/dist` that the backend serves at `/`.

**Notes / fixes surfaced during Phase B:**
- `spa.py` served 403 on the root path (`resolve_within_root` rejects empty candidates before the index fallback); fixed to serve `index.html` directly for `full_path == ""`.
- DTO parity drift fixed: backend `ColumnMappingDTO.case_color` and `VariantPerformanceDTO.case_color` were missing from `frontend_dtos.ts`; added `caseColor?: string | null` mirrors.
- New backend tests: `test_spa_mount_serves_index_and_blocks_api`, `test_security.py` (`resolve_within_root`, `sanitize_upload_filename`), and `test_api_only_mode_root_404` hardened to force API-only mode regardless of repo `frontend/dist` state.

---

## Phase C: File Upload, Profiling & Mapping UI [Complete]

**Goal:** The user can upload an export, see the auto-detected platform/mapping, and adjust the column mapping before transforming.

- [x] Upload dropzone (`POST /api/ingest`) with drag-and-drop, format/size validation (415 / 413 surfaced via the error envelope), and an upload progress state.
- [x] Platform & mapping review screen driven by `POST /api/profile`: display detected platform, confidence, and editable column mapping (`columnMapping`, `parentRowRule`, `cleaningRules`).
- [x] Period picker for `periodStart` / `periodEnd` (ISO `YYYY-MM-DD`).
- [x] Re-run profiling when the user switches sheets or edits headers.

**Success Criteria:**
- Upload → profile → edit mapping → save-as-template round-trips with the live backend.
- A platform mismatch or malformed file renders the 422 `MISSING_REQUIRED_COLUMN` message (not a generic error).

**Notes / fixes surfaced during Phase C:**
- The generated OpenAPI client exposes DTO types only via `components['schemas'][...]` (no named type exports); components import from `components['schemas']` rather than named imports.
- No new backend endpoints were required: the save-as-template round-trip is served by `POST /api/transform` with `saveAsTemplate: true` (writes `mapping_templates`), and re-profile of the same header signature returns `isCached: true` with the stored mapping. The sheet-switch re-profile is driven by `ProfileRequestDTO.activeSheet`.
- Profiling is never fatal: unknown schemas return `platform=UNKNOWN / confidence 0` rather than an error, so the review screen renders a manual platform selector + empty mapping instead of a dead end.
- Upload progress uses `XMLHttpRequest` (`apiClient.uploadFile`) since `fetch` exposes no progress events; the error envelope parser was factored into a shared `envelopeFromText` used by both fetch and XHR paths.

---

## Phase D: Transform & Results UI [Complete]

**Goal:** Run the pipeline and present the report boundary + audit tally.

- [x] Transform action (`POST /api/transform`) with a loading/confirm state; surface `reportedProductCount`, `reportedTotalQty`, `reportedTotalRevenue`, and the **non-zero `skipped*` audit tally** (may be non-zero for valid files — show it as informational, not an error).
- [x] Variant breakdown table (`GET /api/reports/batches/{id}/variants`) with `contributionRatio` rendered as a 0–1 unit share (percentage), toggled by `is_cross_bundling`.
- [x] Product group summary table (`GET /api/reports/batches/{id}/products`).
- [x] Surface `INVALID_VARIANT` (422) from Phase A2 as a per-file validation message naming the offending row.

**Success Criteria:**
- A real transform matches the golden figures in the UI (Shopee 6,910 / TikTok 11,575 units).
- Cross-bundling toggle swaps variant/product data sets correctly.

**Notes / fixes surfaced during Phase D:**
- No backend changes required. Verified live that `variant_analytics` (cross=0) sums **exactly** to the transform `reported*` totals, so the batch-detail page can derive the golden report boundary from `GET /variants?is_cross_bundling=0` even when opened directly (no transform response in navigation state); the transform-response `skipped*` audit tally is only shown when arriving right after a transform.
- Added a `src/utils/format.ts` shared formatter module (`formatCurrency` / `formatNumber` / `formatPercent`) — used by the new page; `BatchesPage` left as-is.
- `useBatchDetail` preloads both cross-bundling datasets so the toggle swaps instantly and the report card never depends on the current toggle; implemented with `useReducer` to satisfy the oxlint `react(set-state-in-effect)` rule.
- Route added: `/batches/:batchId` → `BatchDetailPage`; the transform flow in `UploadPage` navigates there with the `TransformResponseDTO` in router state.

---

## Phase E: Batch Management & Excel Export [Complete]

**Goal:** Manage historical batches and export the executive workbook.

- [x] Batch list screen (`GET /api/reports/batches`) with totals and created-at, plus delete (`DELETE /api/reports/batches/{id}`) with confirmation.
- [x] Batch detail navigation into the Phase D views.
- [x] Export dialog (`GET /api/export/excel?batchIds=`): **pre-validate exactly one batch per platform** to avoid 400 `DUPLICATE_PLATFORM_BATCH`; stream the `.xlsx` via blob download with the `Content-Disposition` filename.
- [x] Cross-batch aggregate view against `GET /api/reports/aggregate` (Phase A3) — dashboard built (in scope).

**Success Criteria:**
- Export of one Shopee + one TikTok batch streams a 4-sheet workbook that opens in Excel with correct totals.
- Selecting two batches for one platform is blocked client-side before the request.

---

## Phase F: Exported Excel Golden Display [Complete]

**Goal:** Make the exported workbook follow the golden file's data display exactly (DevelopmentFeedback20260825): full catalog grid, all product groups and variants shown, values present, and unsold variants rendered per the golden's cell pattern.

**Reference:** `sample_data/expected_output/output_13_19_Jul26.xlsx` (`Produk S`, `Produk T`, `Produk 2 S`, `Produk 2 T`).

- [x] **Full-grid left table** in `backend/app/modules/exporter/report_builder.py` (`render_side_by_side_sheet`): emit EVERY catalog grid row per group (remove the `qty <= 0` skip). Produk sheets emit the full 181-row grid; Produk 2 sheets emit the full 813-row grid.
- [x] **Unsold variant cells:** write the variant name in col B; leave C (qty) and D (revenue) blank exactly like the golden; still write the E contribution formula for every row.
- [x] **Unguarded contribution formulas:** E always `=(C{r}/$H${summary})*100%` (remove `_contribution_or_zero`); zero-total groups therefore cache `#DIV/0!`, reproducing the golden workbook's known defect (user-confirmed). Right-table J stays `=(H{r}/$H$grand_total)*100%` for every group.
- [x] **Always-on SUM ranges:** every group's H/I is `=SUM(C{start}:C{end})` / `=SUM(D{start}:D{end})` over its full contiguous grid span (the Empty-Group literal-0 rule is removed because ranges always exist). TOTAL row unchanged (`=SUM(H2:H{last})`, `=SUM(I2:I{last})`).
- [x] Update the `report_builder.py` docstring (sparse → full) and remove dead helpers.
- [x] **Golden-grid note:** the reference workbook's Produk 2 grids are inconsistent (Produk 2 S = 516 rows vs Produk 2 T = 840 rows, both hand-scaffolded subsets); this app emits its canonical 813-row grid in both sheets as the superset satisfying "show all product groups and variants".
- [x] Rewrite `backend/tests/test_exporter.py` to the new contract:
  - Left-table row count equals the full grid size per sheet (181 / 181 / 813 / 813).
  - Unsold variant rows carry blank C/D plus a formula E; sold rows unchanged.
  - Every group has an in-bounds `=SUM` over its span (replaces `test_empty_groups_have_literal_zero` and `test_no_sum_formula_on_empty_groups`).
  - Zero-total groups' E cells are unguarded formulas (golden `#DIV/0!` behavior; replaces `test_no_div_zero_anywhere`).
  - Keep golden-total conservation (6,910 / 11,575), number formats, anchors, the 36-row Produk 2 Group 9, and right-table completeness.

**Success Criteria:**
- `pytest backend/tests/test_exporter.py` passes; the full backend suite stays green (`pytest backend/tests/`).
- An exported workbook from the sample batch reproduces the golden display (full grid, all variants, golden-style zero cells) with the golden totals unchanged.

---

## Phase G: Batch-Scoped Dashboard Redesign [Complete]

**Goal:** Replace the cross-batch aggregate dashboard with a batch-scoped dashboard: batch selector + Contribution Pie chart + Product sales bar chart + data list, filtered by 3 multi-select checkboxes (Single / Bundling / Cross Bundling).

**Backend (`isBundling` filter):**
- [x] `backend/app/modules/storage/repository.py`: add `is_bundling: bool | int | None = None` to `variant_analytics` (Query A) and `product_group_summary` (Query B). SQL adds `(:is_bundling IS NULL OR is_bundling = :is_bundling)` in the WHERE **and** inside the `product_totals` / `grand_total` CTEs so `contribution_ratio` is computed within the selected subset.
- [x] `backend/app/api/routes.py`: add `is_bundling: int | None = Query(default=None, alias="isBundling")` to `GET /api/reports/batches/{batch_id}/variants` and `GET /api/reports/batches/{batch_id}/products`.
- [x] Regenerate `frontend/src/services/api.ts` via `npm run generate:api` so the client exposes the new `isBundling` query param.
- [x] Tests (`backend/tests/test_api.py`, `backend/tests/test_storage.py`): `isBundling=0&isCrossBundling=0` returns only non-`Bundling*` groups; `isBundling=1` returns only `Bundling*` groups; the qty sums of the two partition equal the unfiltered `isCrossBundling=0` total (Shopee 6,910 / TikTok 11,575 split correctly).

**Frontend (dashboard):**
- [x] Add `recharts` to `frontend/package.json`.
- [x] New hook `src/hooks/useBatchDashboard.ts`: given `batchId` + active `(isCrossBundling, isBundling)` tuples, fetch `/api/reports/batches/{id}/variants` per tuple (up to 3 parallel calls), merge the rows, and compute group rollups client-side (deterministic integer sums) for the charts and summary cards.
- [x] Redesign `src/pages/HomePage.tsx`:
  - Batch selector (from `GET /api/reports/batches`, existing `useBatches` hook).
  - 3 checkboxes (multi-select OR; default all checked): Single (`isCrossBundling=0, isBundling=0`), Bundling (`isCrossBundling=0, isBundling=1`), Cross Bundling (`isCrossBundling=1`).
  - Contribution Pie chart (per-group qty share) + Product sales bar chart (per-group revenue) with recharts.
  - Data list table (variant rows) + summary cards (units / revenue) for the active subset.
- [x] `npm run typecheck`, `npm run lint`, `npm run build` clean.

**Success Criteria:**
- Selecting a batch renders pie/bar/list for the default all-types selection; toggling the checkboxes filters the three datasets in isolation and in combination.
- The `isBundling` filter behaves identically in the UI and the API; no regression in the existing BatchDetail / Export flows.

---

## Phase H: Integration & Packaging [Pending]

**Goal:** Ship a single desktop executable bundling the SPA with the backend (PyInstaller). Renamed from the former Phase F; now runs after the Phase F/G feature work so the packaged smoke test exercises the new display and dashboard.

- [ ] Configure PyInstaller with the SPA build copied into the bundle; verify `sys._MEIPASS` asset resolution and the writable DB path fallback per the `@pyinstaller-packaging-guardian` skill.
- [ ] Automated browser launch on start (skill-configured), hidden console, and clean shutdown.
- [ ] End-to-end smoke test on a clean machine: launch → upload sample `raw_shopee_13_19_Jul26.xlsx` → transform → view the new batch dashboard → export → open workbook (golden display).

**Success Criteria:**
- The packaged `.exe` serves the SPA (including the new batch dashboard), persists to `%LOCALAPPDATA%/RAESmartReport`, and reproduces the golden workbook from the sample files.

---

## Verification Plan

```powershell
# Backend (Phases A)
pytest backend/tests/ -v
ruff check backend/

# Frontend (Phases B–G)
cd frontend
npm run generate:api   # re-run after Phase G backend changes to pick up isBundling
npm run typecheck
npm run build

# Packaging (Phase H)
pyinstaller packaging.spec   # then launch the produced .exe
```

Regression anchors: golden totals must stay fixed (Shopee 6,910 / Rp 525,973,986; TikTok 11,575 / Rp 658,458,817), and the R1 reconciliation invariant must hold (`grid qty + skipped qty == persisted qty` for both platforms).

---

# Handoff Brief

- **Current Phase:** Phase G (Batch-Scoped Dashboard Redesign) — **complete**.
- **2026-08-25 Scope extension applied:** `DevelopmentFeedback20260825.md` added two feature phases — **Phase F (Exported Excel Golden Display, backend exporter)** and **Phase G (Batch-Scoped Dashboard Redesign, backend `isBundling` filter + frontend recharts)** — and renamed the packaging work to **Phase H** (the final milestone, runs after F/G). Per the STOP protocol, the next session starts the final **Phase H**. This Handoff Brief will be updated again at the end of each phase.
- **Done so far (Phase G):**
  - **Backend `isBundling` filter:** `backend/app/modules/storage/repository.py` — `variant_analytics` (Query A) and `product_group_summary` (Query B) accept `is_bundling: bool | int | None = None`; both SQL CTEs (`product_totals` / `grand_total`) **and** the outer WHERE apply `(:is_bundling IS NULL OR is_bundling = :is_bundling)` so `contribution_ratio` is computed within the selected partition. New `_coerce_bundling_flag` normalizes the binding. `backend/app/api/routes.py` — `is_bundling: int | None = Query(default=None, alias="isBundling")` added to `GET /variants` and `GET /products`.
  - **API client regen:** `frontend/src/services/api.ts` regenerated from the live `/openapi.json` (now exposes `isBundling?: number | null`); `apiClient.batchVariants`/`batchProducts` gained an optional `isBundling` param (`is_cross_bundling` stays `snake_case` on the wire; `isBundling` is the camelCase alias).
  - **Frontend dashboard:** added `recharts`. New `src/hooks/useBatchDashboard.ts` — fetches the 3 partition datasets in parallel (`is_cross_bundling=0,isBundling=0` / `=0,isBundling=1` / `is_cross_bundling=1`), tags rows by `source`, merges the active selection, and computes group rollups client-side (deterministic integer sums + 0–1 qty share). `src/pages/HomePage.tsx` redesigned: batch selector (default newest), 3 multi-select checkboxes (Single / Bundling / Cross Bundling, default all), summary cards (rows / units / revenue), recharts Contribution Pie + Product sales Bar, and a variant data-list table with a per-row type badge and global share.
  - **Phase G verification (live server, temp DB):**
    - `pytest backend/tests/` = **227 passed** (6 new: `test_query_a_is_bundling_partition`, `test_query_a_is_bundling_tiktok`, `test_query_b_is_bundling_partition`, `test_variants_is_bundling_partition`, `test_variants_is_bundling_tiktok`, `test_products_is_bundling_partition`); `ruff check backend/` clean.
    - Partition invariant holds through both the repository and the HTTP API: Shopee 6,553 (Single) + 357 (Bundling) = **6,910**; TikTok 11,377 + 198 = **11,575**; `Bundling*` groups ⟺ `is_bundling=1` exactly; per-group variant ratios sum to 1.0 within each partition (zero-qty groups yield 0.0 ratios); Query B group ratios partition the subset total.
    - `npm run typecheck`, `npm run lint`, `npm run build` all clean (build warns only about the recharts-inflated chunk size; acceptable for a local SPA).
    - Live-server smoke: seeded both sample batches through `ingest → profile → transform`, then issued the exact three query strings `useBatchDashboard` sends and confirmed the partitions (6,910 / 11,575 / cross 7 / 13); the SPA mount served the freshly built dashboard bundle at `/`.
    - Bridge doc `.agents/skills/fullstack-bridge-contract/references/api_endpoints.md` updated with the `isBundling` query param on both endpoints.
  - **No regression** in existing BatchDetail (`useBatchDetail`/`BatchDetailPage`) or Export flows — their endpoint call shapes are unchanged (they pass only `is_cross_bundling`).
- **What is next (fresh session):**
  1. Phase H (Integration & Packaging) — the final milestone: PyInstaller with the SPA build bundled, `sys._MEIPASS` asset resolution, writable DB path fallback (`%LOCALAPPDATA%/RAESmartReport`), automated browser launch, hidden console, clean shutdown, and the clean-machine smoke test reproducing the golden workbook from the sample files (launch → upload `raw_shopee_13_19_Jul26.xlsx` → transform → view the new batch dashboard → export → open the workbook).
- **Artifacts:**
  - This plan: `docs/plan/FrontendDevelopmentPlan.md`
  - Backend plan: `docs/plan/BackendImplementationPlan.md`
  - Bridge contract: `.agents/skills/fullstack-bridge-contract/`
