# REST API Endpoint Catalog

> **Canonical source of truth:** the OpenAPI specification served by FastAPI at
> `/openapi.json` (interactive docs at `/docs`). This catalog is a human-readable
> summary and must match `routes.py` 1:1. Regenerate the TypeScript client from
> `/openapi.json` (e.g. `openapi-typescript`); do not hand-roll DTOs.

| Method | Endpoint | Description | Request | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Liveness probe; the packaged desktop launcher polls this before opening the browser | None | `HealthDTO` |
| `POST` | `/api/ingest` | Uploads a spreadsheet, returns structural metadata + sample rows | `multipart/form-data` field `file` | `IngestionResultDTO` |
| `POST` | `/api/profile` | Detects the platform adapter, or returns a cached mapping template by header signature | `ProfileRequestDTO` | `ProfilerResponseDTO` |
| `POST` | `/api/transform` | Runs the ELT pipeline, persists the batch to SQLite, returns the report summary + audit tally | `TransformAndSaveRequestDTO` | `TransformResponseDTO` |
| `GET` | `/api/reports/batches` | Lists all persisted batches, newest first | None | `BatchSummaryDTO[]` |
| `GET` | `/api/reports/batches/{batchId}/variants` | Query A: variant-level breakdown for a batch | Query `?is_cross_bundling=` (int, default `0`), `?isBundling=` (int 0/1, optional) | `VariantPerformanceDTO[]` |
| `GET` | `/api/reports/batches/{batchId}/products` | Query B: master product group rollups for a batch | Query `?is_cross_bundling=` (int, default `0`), `?isBundling=` (int 0/1, optional) | `ProductSummaryDTO[]` |
| `GET` | `/api/reports/batches/{batchId}/unreported` | Query G: persisted non-reportable entries for a batch (`is_reported = 0`; off-grid variants, non-catalog products) | None | `UnreportedVariantDTO[]` |
| `GET` | `/api/reports/aggregate` | Query C: multi-batch / multi-platform / date-range aggregation | Query `?platform=`, `?periodStart=`, `?periodEnd=`, `?isCrossBundling=` (all optional) | `AggregateRowDTO[]` |
| `DELETE` | `/api/reports/batches/{batchId}` | Cascade-deletes a batch from `transaction_items` | None | `DeleteBatchResponseDTO` |
| `GET` | `/api/export/excel` | Streams a 4-sheet executive workbook (+ `Tidak Terlaporkan S/T` when unreported entries exist) | Query `?batchIds=` (one batch per platform) | Binary `.xlsx` stream |

> **Query-parameter casing:** JSON bodies are strictly `camelCase`. The
> `is_cross_bundling` query parameter on the variant/product endpoints is
> `snake_case` because it is bound directly to the FastAPI parameter name. The
> `isBundling` filter (0 = Single, 1 = Bundling, omitted = both) is declared
> with an explicit `camelCase` alias on the same endpoints. The aggregate
> endpoint's filters are all `camelCase` (`isCrossBundling`), declared with
> explicit aliases. A generated OpenAPI client will name them correctly.
> `batchIds` is declared with an explicit `camelCase` alias.

## Standard Error Response Structure

All 4xx/5xx responses use a single envelope. `details` is **omitted when null**
(client types should make it optional):

```json
{
  "status": "error",
  "code": "MISSING_REQUIRED_COLUMN",
  "message": "[SHOPEE] Missing required column(s): ['Produk', ...]",
  "details": [
    {
      "type": "missing",
      "loc": ["body", "columnMapping", "productGroup"],
      "msg": "Field required"
    }
  ]
}
```

### Error codes

| Code | HTTP | Meaning |
| :--- | :--- | :--- |
| `VALIDATION_ERROR` | 422 | Pydantic request body validation failed (`details` carries the field errors) |
| `MISSING_REQUIRED_COLUMN` | 422 | Uploaded file lacks a platform's required columns for the declared platform |
| `INVALID_SPREADSHEET` | 422 | Spreadsheet could not be parsed |
| `EMPTY_SPREADSHEET` | 422 | Spreadsheet has no data rows |
| `SHEET_NOT_FOUND` | 404 | Requested sheet name does not exist |
| `UNSUPPORTED_FORMAT` | 415 | File is not `.xlsx` or `.csv` |
| `HTTP_ERROR` | varies | Generic `HTTPException` (e.g. 400 upload empty, 404 batch not found, 413 too large) |
| `INTERNAL_ERROR` | 500 | Unexpected exception |
| `INVALID_VARIANT` | 422 | A data row violates a validated business rule (e.g. same-shade pack of N>2) |

## Notes for the frontend

- **Transform response totals.** `reportedProductCount` / `reportedTotalQty` /
  `reportedTotalRevenue` mirror the exported workbook (grid-intersected,
  `is_reported = 1` only). `skippedCount` / `skippedQty` / `skippedRevenue`
  are the **dash-row-only** excluded volume tally (parent summaries); these
  fields **may be non-zero for valid files** — surface them rather than
  treating them as an error. `unreportedCount` / `unreportedQty` /
  `unreportedRevenue` are the persisted non-reportable entries (off-grid
  variants, non-catalog products) that are stored and viewable via
  `GET /api/reports/batches/{batchId}/unreported` but never reach a report
  figure.
- **Batch list totals.** `BatchSummaryDTO.grandTotalQty` /
  `grandTotalRevenue` are storage-level raw sums of **reported rows**
  (`is_reported = 1`) **including** cross-bundling rows, and deliberately
  differ from the transform `reported*` figures. They are not the workbook
  totals. Unreported volume is never included here.
- **Export constraint.** `/api/export/excel` requires **exactly one batch per
  platform**. It returns 400 `DUPLICATE_PLATFORM_BATCH` if two batches for the
  same platform are selected and 404 if any `batchIds` is unknown. The export
  dialog should pre-validate selection. The `Content-Disposition` filename is
  the source `importBatchId` (batch ids joined with `_` when both platforms
  are exported), so the downloaded file traces back to its source batch.
