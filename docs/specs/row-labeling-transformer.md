# Module Specification: Row Labeling & Transformation Engine

## 1. Overview
The Row Labeling Engine processes raw records from the ingestion stage, eliminates parent/subtotal rows to prevent double-counting, extracts clean variant names, flags product bundling, and prepares atomic labeled records for direct batch insertion into SQLite.

## 2. Processing Pipeline
1. Raw Tabular Data
│
▼
2. Row Filtering (Prune Parent/Subtotal Rows where variant is '-' or empty)
│
▼
3. String Normalization (Strip packaging suffixes: "Random Keychain", "Tanpa Keychain")
│
▼
4. Bundle Detection (Flag isBundling = true for '+' or combo items)
│
▼
5. Generate Labeled Records Batch (Ready for SQLite Transactional Insert)

## 3. Transformation Rules

### 3.1 Parent Row Filtering (Double-Counting Prevention)
- Marketplaces often include an aggregate/parent row (e.g., `Nama Variasi: "-"`, containing the sum of all child variants).
- **Rule:** If `rawVariant` equals `"-"`, `""`, or matches the defined `parentRowRule`, the row MUST be excluded from database insertion.

### 3.2 Variant Normalization & Bundling Detection
- **Packaging Suffix Stripping:** Extract core variant names by stripping packaging gimmicks (e.g., `"Brave,Random Keychain"` $\rightarrow$ `"Brave"`, `"Active,Tanpa Keychain"` $\rightarrow$ `"Active"`).
- **Bundle / Combo Detection:** Identify bundling delimiters (e.g., `+`, `&`, `Bundling`). Set `isBundling = true` if multiple variant tokens are present.

## 4. Batch Record Structure

```python
class LabeledTransactionRecord:
  importBatchId: str
  platform: str
  periodStart?: Date
  periodEnd?: Date
  productGroup: str
  rawVariant: str
  cleanVariant: str
  isBundling: bool
  sku?: str
  qtySold: int
  revenue: float
}