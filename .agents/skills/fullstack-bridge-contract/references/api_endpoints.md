# REST API Endpoint Catalog

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/files/upload` | Ingests spreadsheet file, parses delimiter and headers | `multipart/form-data` | `IngestionResultDTO` |
| `POST` | `/api/profiler/profile` | Profiles raw headers via cache hash or LLM | `{ fileId: string, sheet?: string }` | `ProfilerResponseDTO` |
| `POST` | `/api/transformer/process` | Filters parent rows, cleans, inserts into SQLite | `TransformAndSaveRequestDTO` | `{ batchId: string, insertedCount: number }` |
| `GET` | `/api/reports/batches` | Lists all historical import batches | None | `BatchSummaryDTO[]` |
| `GET` | `/api/reports/variant-performance` | Query A: Variant breakdown for a batch | Query Param: `?batchId=xyz` | `VariantPerformanceDTO[]` |
| `GET` | `/api/reports/product-summary` | Query B: Master product group summary | Query Param: `?batchId=xyz` | `ProductSummaryDTO[]` |
| `GET` | `/api/reports/export-excel` | Generates and streams formatted `.xlsx` | Query Param: `?batchId=xyz` | Binary `.xlsx` File Stream |
| `DELETE`| `/api/reports/batches/{batchId}` | Deletes a batch from `transaction_items` | None | `{ success: boolean }` |

## Standard Error Response Structure

```json
{
  "status": "error",
  "code": "INVALID_MAPPING",
  "message": "Column 'Jumlah' could not be resolved in the uploaded spreadsheet.",
  "details": null
}
```
