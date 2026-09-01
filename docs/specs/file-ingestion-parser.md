# Module Specification: File Ingestion & Parser

## 1. Overview
The File Ingestion module accepts raw spreadsheet files (`.xlsx`, `.xls`, `.csv`), validates file integrity, handles multi-sheet selection, enforces locale-pinned number/currency parsing, extracts structural metadata, and serves sampled subsets of rows for downstream schema profiling and ingestion without mutating underlying data types.

---

## 2. Technical Requirements & Boundaries

### 2.1 Supported Formats & Constraints
- **File Formats:** `.xlsx`, `.xls`, `.csv`
- **Max File Size:** 50 MB
- **CSV Delimiter Detection:** Auto-detect comma (`,`), semicolon (`;`), and tab (`\t`).
- **Encoding & Mojibake Tolerance:** UTF-8 / Windows-1252 auto-detection with fallback to UTF-8. Must handle corrupted replacement characters and mojibake in product titles (e.g., `Winona's Ombre Picks - \ufffd`) gracefully without failing parsing or corrupting text.

### 2.2 Functional Capabilities

#### 1. Multi-Sheet Detection & Selection
- Multi-sheet detection for `.xlsx` / `.xls`: Inspect workbook structure and return all available sheet names.
- **Platform-Specific Default Sheet Mapping:**
  - **Shopee:** Default to `Produk dengan Performa Terbaik` (the relevant product performance sheet among the 7 sheets present in standard Shopee exports).
  - **TikTok Shop:** Default to `Sheet1`.
  - **Lazada:** Default to `Produk` (single-sheet workbook).
  - **Fallback / Generic:** Prompt user selection or default to the first active/non-empty data sheet.

#### 1b. Preamble-Aware Header Detection
- Lazada workbooks prefix the real header row with ~5 metadata/source preamble rows (each populated with exactly 1 cell, e.g. `Sumber Data : Lazada - ...`).
- The reader skips leading rows with **fewer than 2 non-empty cells** before treating a row as the header row. Verified no regression: Shopee (40-cell), TikTok Shop / Tokopedia (7-cell) header rows are already the first row, so they are unaffected.

#### 2. Deterministic Locale-Pinned Number & Currency Sanitization
- **Strict id-ID Locale Pinning:** All marketplace exports in scope follow the Indonesian format where `.` is the thousands separator and `,` is the decimal separator.
  - Examples: `Rp 50.000` $\rightarrow$ `50000`, `Rp 261.911.314` $\rightarrow$ `261911314`, `149.000` $\rightarrow$ `149000`, `261.911.314,50` $\rightarrow$ `261911314.50`.
- **Zero Per-Value Heuristics:** Never use dynamic per-value heuristic dot detection (e.g. guessing that a single dot with 3 trailing digits like `50.000` is a decimal point). Per-value heuristics cause silent 1000x under-counting on round retail IDR prices.
- **Accounting Formatting & Negative Values:** Strip currency identifiers (`Rp`, `IDR`, `IDR `), whitespace, and correctly handle negative values represented via minus signs (`-Rp 1.000` $\rightarrow$ `-1000`) or financial parentheses (`(1.000)` $\rightarrow$ `-1000`).

#### 3. Metadata & Sampling Extraction
- Extract column header list (`raw_headers: List[str]`).
- Extract total estimated row count.
- Extract the top 10 non-empty rows (`sample_rows: List[Dict[str, Any]]`) for verification and fallback LLM schema analysis.

---

## 3. Data Contracts & Interfaces

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Dict, Any, Optional

class IngestionResult(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    file_id: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    detected_delimiter: Optional[str] = None
    available_sheets: List[str]
    active_sheet: str
    total_rows: int
    raw_headers: List[str]
    sample_rows: List[Dict[str, Any]]
```
