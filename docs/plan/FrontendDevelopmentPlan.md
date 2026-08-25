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

## Phase E: Batch Management & Excel Export [Pending]

**Goal:** Manage historical batches and export the executive workbook.

- [ ] Batch list screen (`GET /api/reports/batches`) with totals and created-at, plus delete (`DELETE /api/reports/batches/{id}`) with confirmation.
- [ ] Batch detail navigation into the Phase D views.
- [ ] Export dialog (`GET /api/export/excel?batchIds=`): **pre-validate exactly one batch per platform** to avoid 400 `DUPLICATE_PLATFORM_BATCH`; stream the `.xlsx` via blob download with the `Content-Disposition` filename.
- [ ] Cross-batch aggregate view against `GET /api/reports/aggregate` (Phase A3) if the dashboard is in scope.

**Success Criteria:**
- Export of one Shopee + one TikTok batch streams a 4-sheet workbook that opens in Excel with correct totals.
- Selecting two batches for one platform is blocked client-side before the request.

---

## Phase F: Integration & Packaging [Pending]

**Goal:** Ship a single desktop executable bundling the SPA with the backend (PyInstaller).

- [ ] Configure PyInstaller with the SPA build copied into the bundle; verify `sys._MEIPASS` asset resolution and the writable DB path fallback per the `@pyinstaller-packaging-guardian` skill.
- [ ] Automated browser launch on start (skill-configured), hidden console, and clean shutdown.
- [ ] End-to-end smoke test on a clean machine: launch → upload sample `raw_shopee_13_19_Jul26.xlsx` → transform → export → open workbook.

**Success Criteria:**
- The packaged `.exe` serves the SPA, persists to `%LOCALAPPDATA%/RAESmartReport`, and reproduces the golden workbook from the sample files.

---

## Verification Plan

```powershell
# Backend (Phases A)
pytest backend/tests/ -v
ruff check backend/

# Frontend (Phases B–E)
cd frontend
npm run generate:api
npm run typecheck
npm run build

# Packaging (Phase F)
pyinstaller packaging.spec   # then launch the produced .exe
```

Regression anchors: golden totals must stay fixed (Shopee 6,910 / Rp 525,973,986; TikTok 11,575 / Rp 658,458,817), and the R1 reconciliation invariant must hold (`grid qty + skipped qty == persisted qty` for both platforms).

---

# Handoff Brief

- **Current Phase:** Phase D (Transform & Results UI) — **complete**. Per the STOP protocol, Phase E starts in a fresh session.
- **Done so far (Phase D):**
  - `src/pages/BatchDetailPage.tsx` + route `/batches/:batchId`: report-boundary summary cards (platform/period, product groups, total units, total revenue), an informational audit tally card (`insertedCount` / `skippedCount` / `skippedQty` / `skippedRevenue` / `warningCount`, only when arriving from a transform), a cross-bundling toggle, the variant breakdown table, and the product group summary table — `contributionRatio` rendered as a 0–1 unit share percentage, totals in `id-ID` formatting.
  - `src/hooks/useBatchDetail.ts`: `useReducer`-based loader fetching both cross-bundling states of `/variants` and `/products` in parallel (toggle swaps instantly; report card derived from cross=0 always).
  - `src/utils/format.ts`: shared `formatCurrency` / `formatNumber` / `formatPercent`.
  - `src/components/MappingEditor.tsx`: primary action is now **Run transform & save** with an inline confirm step (Run/Cancel) and a "Running…" loading state; `saveAsTemplate: true` retained so the mapping template caches.
  - `src/pages/UploadPage.tsx`: on a successful transform, navigates to `/batches/{id}` carrying the `TransformResponseDTO` in router state (back button returns to a fresh upload flow).
  - `src/hooks/useUploadFlow.ts`: renamed `saveAsTemplate` → `runTransform`.
- **Phase D verification (live backend, temp DB):**
  - Shopee transform → **6,910 / Rp 525,973,986**; TikTok transform → **11,575 / Rp 658,458,817** (golden match in the response that drives the UI).
  - `/variants` cross=0 sums exactly to the golden totals (155 Shopee / 93 TikTok rows); cross=1 swaps the dataset (45 / 14 rows) — toggle swap verified.
  - `contributionRatio` confirmed in [0,1]; product rollups sum to golden totals.
  - Same-shade 3-pack CSV → 422 `INVALID_VARIANT` naming shade 'Dynamic', the raw variant, and SKU `(no SKU)`.
  - `npm run typecheck`, `npm run lint`, `npm run build` clean; SPA serves `/batches/:id` and the new bundle at `/`.
  - No backend changes; backend suite remains green (**221 tests**).
- **What is next (fresh session):**
  1. Phase E (Batch Management & Excel Export): batch list with delete (`DELETE /api/reports/batches/{id}`), batch-detail navigation from the list, export dialog (`GET /api/export/excel?batchIds=` with pre-validation of exactly one batch per platform), and the cross-batch aggregate view against `GET /api/reports/aggregate`.
- **Artifacts:**
  - This plan: `docs/plan/FrontendDevelopmentPlan.md`
  - Backend plan: `docs/plan/BackendImplementationPlan.md`
  - Bridge contract: `.agents/skills/fullstack-bridge-contract/`
