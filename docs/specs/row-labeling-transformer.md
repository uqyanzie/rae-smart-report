# Module Specification: Row Labeling & Transformation Engine

## 1. Overview
The Row Labeling Engine transforms raw extracted rows into clean, atomic, normalized records ready for SQLite transactional persistence and catalog-driven aggregation. It eliminates double-counting parent rows, executes deterministic multi-step variant normalization, applies domain-specific same-shade fold-back rules, routes intra- versus cross-family bundles, and flags unmapped tokens.

---

## 2. Processing Pipeline

```text
Raw Tabular Data Rows
       │
       ▼
1. Parent Row Pruning ───► (Prune if variant == '-' or matches parentRowRule)
       │
       ▼
2. Brand Prefix Normalization ───► (Strip 'Raecca ' prefix across platforms for uniform joins)
       │
       ▼
3. Token Cleaning & Regex Sanitization ───► (Strip ordinals '05.', packaging suffixes 'Random Keychain')
       │
       ▼
4. Catalog & Alias Resolution ───► (Map 'Cheerfull'->'Cheerful', 'Ov Hype'->'Over Hype', isolate caseColor)
       │
       ▼
5. Same-Shade 2-Pack Fold-Back ───► (Fold same-shade pairs into single row: 1x rev, 2x qty; aggregate duplicates)
       │
       ▼
6. Bundle Routing & Tagging ───► (Tag isBundling, isCrossFamily; surface unmapped tokens)
       │
       ▼
Atomic Labeled Records Batch (SQLite Transactional Insert)
```

---

## 3. Transformation & Normalization Rules

### 3.1 Deterministic Parent Row Elimination
- **Shopee:** Rows with `Nama Variasi == "-"` represent aggregate product headers. These MUST be dropped prior to insertion to prevent double-counting (~295 rows per monthly export).
- **TikTok Shop:** Rows are already atomic at the SKU level (`parentRowRule = None`). No rows are dropped.

### 3.2 Product Group Brand Prefix Reconciliation
- Standardize `product_group` strings across platforms by normalizing brand prefixes (e.g. stripping leading `Raecca `) so that products from Shopee and TikTok Shop join cleanly under identical canonical master group names.

### 3.3 Variant Normalization Rules
Variant strings undergo multi-pass cleaning and canonical alias resolution:

| Pattern Type | Raw Example | Normalized Result | Handling Logic |
| :--- | :--- | :--- | :--- |
| **Packaging Suffix** | `Brave,Random Keychain`, `Active / Tanpa Keychain` | `Brave`, `Active` | Strip gimmick suffixes via regex/keyword filter |
| **Ordinal Prefix** | `05. Dynamic`, `01 Peony`, `08. Gorgeous` | `Dynamic`, `Peony`, `Gorgeous` | Strip leading digits and punctuation (`^\d+[\.\s-]*`) |
| **Misspelling** | `Cheerfull` | `Cheerful` | Global alias lookup table |
| **Abbreviation** | `Ov Hype`, `BunPink`, `WildMauv`, `HipRose` | `Over Hype`, `Bunny Pink`, `Wild Mauve`, `Hippie Rose` | Family-scoped alias lookup table |
| **Suffix Elision** | `Kind` (under Power Frosted) | `Kind Power` | Family-scoped alias lookup table |
| **Case Colour** | `Bunny Pink,Matcha Strawberry` | Variant: `Bunny Pink`<br>Case Color: `Matcha Strawberry` | Extract into `case_color` for traceability, then **ignore for reporting** — TJB totals aggregate by shade across all colours. Unknown colour names are safe to skip. |
| **Pack Annotation** | `Lip Moist (2pcs)` | `Lip Moist` (Multiplier = 2) | Extract unit multiplier |
| **Delimiters** | `Active / Tanpa Keychain`, `Active, Brave` | Split on `/`, `,`, and `+` | Multi-token delimiter parsing |

### 3.4 Unmapped Token Safety Guarantee
- Any token that cannot be resolved against the authoritative product catalog and alias maps MUST be surfaced as an **unmapped token warning** in the transformation result. Tokens must **never** be silently discarded, dropped, or hallucinated, as that would cause revenue to vanish.

---

## 4. Same-Shade 2-Pack Fold-Back Rule

Shopee sells same-shade 2-packs within bundle product listings (e.g., product `Bundling Glow Up Tint` with variant `Dynamic,05. Dynamic` or `Energic,06. Energic`). Because the combinatorial bundle grid is strictly $C(n,2)$ (unordered pairs of *distinct* shades), same-shade combinations have no dedicated bundle grid cell.

### 4.1 Fold-Back Transformation Logic
When an intra-family bundle record contains two identical shades:
1. **Quantity Scaling:** Multiply the sold quantity by **2** (one 2-pack sale moves 2 units of that shade).
2. **Revenue Allocation:** Allocate **100% of the revenue as-is** (1x).
3. **Target Routing:** Fold the record into the corresponding **single-shade variant row** within the parent product group (e.g., add to `Glow Up Tint -> Dynamic`).
4. **Duplicate Row Aggregation:** If multiple same-shade rows occur in raw data (e.g. `Gorgeous,08. Gorgeous` appearing multiple times or with 0 qty), aggregate all matching rows before fold-back.
5. **Strict Multiplicity Boundary:** Intra-family token counts in empirical data are strictly $N \le 2$. The fold-back rule is strictly bounded to $N=2$. If any raw record contains $N > 2$ identical shades, the pipeline must **raise a loud validation error** rather than guessing a multiplier.

---

## 5. Intra-Family vs. Cross-Family Bundle Classification

- **Single Products:** Exactly 1 shade token from 1 product family $\rightarrow$ Routes to `Produk S` / `Produk T` (Table 1, single group).
- **Intra-Family Bundles:** 2 distinct shade tokens from the *same* family (e.g. `Active + Brave`) $\rightarrow$ Routes to `Produk S` / `Produk T` (Table 1, bundle group).
- **Cross-Family Bundles (*Bundling Silang*):** Tokens spanning 2 distinct product families (e.g. `Glow Up Tint & Over The Glaze`, `Over The Glaze & Tinted Jelly Balm`) $\rightarrow$ Routes to `Produk 2 S` / `Produk 2 T`.

---

## 6. Labeled Record Data Contract

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from datetime import date

class LabeledTransactionRecord(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    import_batch_id: str
    platform: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    product_group: str
    raw_variant: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool = False  # persisted column name; "bundling silang"
    case_color: Optional[str] = None
    sku: Optional[str] = None
    qty_sold: int
    revenue: int  # exact integer IDR, matching BigInteger storage
    unit_multiplier: int = 1
```