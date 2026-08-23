# Module Specification: File Ingestion & Parser

## 1. Overview
The File Ingestion module accepts raw spreadsheet files (`.xlsx`, `.xls`, `.csv`), validates file integrity, extracts structural metadata, and serves sampled subsets of rows for downstream schema profiling without mutating underlying data types.

## 2. Technical Requirements & Boundaries

### 2.1 Supported Formats & Constraints
- **File Formats:** `.xlsx`, `.xls`, `.csv`
- **Max File Size:** 50 MB
- **CSV Delimiter Detection:** Auto-detect comma (`,`), semicolon (`;`), and tab (`\t`).
- **Encoding:** UTF-8 / Windows-1252 auto-detection with fallback to UTF-8.

### 2.2 Functional Capabilities
1. **File Parsing:**
   - Multi-sheet detection for `.xlsx` / `.xls`: Return sheet names and target specific sheets (defaulting to the first active sheet).
   - Numerical parsing: Sanitize currency/accounting strings (e.g., `Rp 261.911.314`, `261.911.314,00`, `$1,200.50`) into standard floats/integers.
2. **Metadata & Sampling Extraction:**
   - Extract column header list (`rawHeaders: string[]`).
   - Extract total estimated row count.
   - Extract the top 10 non-empty rows (`sampleRows: Record<string, any>[]`) for AI schema analysis.

## 3. Data Contracts & Interfaces

```python
class IngestionResult:
  fileId: str
  fileName: str
  fileSize: float
  mimeType: str
  detectedDelimiter: str
  availableSheets: str[]
  activeSheet: str
  totalRows: int
  rawHeaders: str[]
  sampleRows: Dict[str, Any]
```
