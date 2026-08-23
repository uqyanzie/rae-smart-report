# Module Specification: AI Schema Profiler & Mapping Engine

## 1. Overview
The Schema Profiler maps disparate e-commerce export formats (Shopee, TikTok Shop, Tokopedia, Lazada) into a canonical internal schema. It implements a **three-tier resolution architecture**:
1. **Tier 1: Hardcoded Platform Adapters (Primary)** for known marketplace exports with exact header matching.
2. **Tier 2: SHA-256 Header Signature Cache** for user-verified custom mappings.
3. **Tier 3: LLM Schema Profiler (Fallback)** for unknown formats, subject to mandatory human confirmation before ingestion.

---

## 2. Canonical Target Schema
All ingested data must resolve to these canonical attributes:
- `productGroup` (string, required): Master product name / group (e.g., "Glow Up Tint").
- `rawVariant` (string, required): Original variant string as exported by the marketplace.
- `sku` (string, optional): Stock Keeping Unit identifier.
- `qtySold` (integer, required): Units sold within the period (must strictly reflect shipped/ready-to-ship orders).
- `revenue` (number / integer cents, required): Total net sales value (must strictly reflect shipped/ready-to-ship orders).
- `caseColor` (string, optional): Tinted Jelly Balm case colour (e.g. "Fizzy Pop", "Buttered Yellow"). Captured for SKU traceability only — **not a reporting dimension**; TJB totals aggregate by shade across all case colours.
- `parentRowRule` (object, optional): Rule to identify and prune aggregated parent rows or summary rows (omitted for platforms with purely atomic SKU-level rows).

---

## 3. Tier 1: Pinned Platform Adapters (Hardcoded)

To guarantee 100% precision and eliminate ambiguity, known marketplace exports are mapped deterministically via hardcoded adapters.

### 3.1 Shopee Adapter (`Produk dengan Performa Terbaik`)
| Canonical Field | Exact Source Header | Notes |
| :--- | :--- | :--- |
| `productGroup` | `Produk` (Col B) | Product name |
| `rawVariant` | `Nama Variasi` (Col E) | Variant name |
| `sku` | `SKU Induk` (Col H) | Parent SKU |
| `qtySold` | `Produk (Pesanan Siap Dikirim)` (Col S) | **Shipped orders only** |
| `revenue` | `Penjualan (Pesanan Siap Dikirim) (IDR)` (Col J) | **Shipped orders only** |
| `parentRowRule` | `targetColumn: "Nama Variasi"`, `ignoreCondition: "EQUALS_DASH"` | Prunes 295 parent rows where `Nama Variasi == "-"` |

> [!IMPORTANT]
> **Shipped Orders vs. Created Orders:** Shopee provides both `Pesanan Dibuat` (created) and `Pesanan Siap Dikirim` (ready to ship). Created orders include unpaid and cancelled transactions, overstating net revenue by ~11.85%. Full column name matching is required because the header contains 9 columns containing `Siap Dikirim`.

### 3.2 TikTok Shop Adapter (`Sheet1`)
| Canonical Field | Exact Source Header | Extraction Logic |
| :--- | :--- | :--- |
| `productGroup` | `Produk` (Col C) | Substring **before** `:` |
| `rawVariant` | `Produk` (Col C) | Substring **after** `:` |
| `sku` | `SKU ID` (Col A) | SKU identifier |
| `qtySold` | `Produk terjual` (Col G) | Quantity sold |
| `revenue` | `GMV` (Col E) | Gross Merchandise Value / Revenue |
| `parentRowRule` | `None` | **No parent rows exist** (0 of 270 rows). All rows are atomic at SKU level. |

---

## 4. Tier 2 & 3: Fallback LLM Profiler & Guardrails

For unknown marketplace exports where no hardcoded adapter or cached signature matches:

### 4.1 LLM Boundary & Guardrails
- **Zero Math Responsibility:** The LLM is NEVER used to perform calculations, summations, or percentage metrics.
- **Optional `parentRowRule`:** The LLM must not be forced to invent a parent row rule if the export is already atomic.
- **Mandatory Human Verification:** LLM profiling outputs must be presented in the UI for user review and approval before persisting to `mapping_templates` or running ingestion.

### 4.2 LLM Output Schema Contract

```json
{
  "platform": "SHOPEE" | "TIKTOK_SHOP" | "TOKOPEDIA" | "LAZADA" | "UNKNOWN",
  "confidence": 0.95,
  "columnMapping": {
    "productGroup": "Produk",
    "rawVariant": "Nama Variasi",
    "sku": "SKU Induk",
    "qtySold": "Produk (Pesanan Siap Dikirim)",
    "revenue": "Penjualan (Pesanan Siap Dikirim) (IDR)",
    "caseColor": null
  },
  "parentRowRule": {
    "targetColumn": "Nama Variasi",
    "ignoreCondition": "EQUALS_DASH"
  },
  "suggestedCleaningRules": [
    {
      "pattern": "^\\d+\\.\\s*",
      "replacement": "",
      "description": "Strip ordinal prefix numbers like '05. Dynamic'"
    }
  ]
}
```

```python
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional, List
from enum import Enum

class IgnoreCondition(str, Enum):
    EQUALS_DASH = "EQUALS_DASH"
    IS_EMPTY = "IS_EMPTY"
    CONTAINS_TOTAL = "CONTAINS_TOTAL"

class ParentRowRuleDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    target_column: str
    ignore_condition: IgnoreCondition

class ColumnMappingDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    product_group: str
    raw_variant: str
    sku: Optional[str] = None
    qty_sold: str
    revenue: str
    case_color: Optional[str] = None

class CleaningRuleDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    pattern: str
    replacement: str
    description: str

class ProfilerResultDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    platform: str
    confidence: float = Field(ge=0.0, le=1.0)
    column_mapping: ColumnMappingDTO
    parent_row_rule: Optional[ParentRowRuleDTO] = None
    suggested_cleaning_rules: List[CleaningRuleDTO] = []
```