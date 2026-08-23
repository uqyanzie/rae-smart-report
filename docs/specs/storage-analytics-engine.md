# Module Specification: Storage & SQL Analytics Engine

## 1. Overview
The Storage module provides persistent local data management using an embedded SQLite database managed via Python (SQLAlchemy / SQLModel). It implements an ELT pattern: normalized and labeled line-item transactions are ingested into atomic tables, while executive reports, summary metrics, and Excel export datasets are computed on-demand through optimized SQL queries (`GROUP BY`, `SUM`, Common Table Expressions).

> [!IMPORTANT]
> **Grid Population Semantics:** SQL aggregation queries are used strictly to **populate metrics into a declaratively generated catalog grid**. The SQL queries do *not* define the output row structure or row order, because the executive report requires fixed combinatorial rows (e.g. $C(n,2)$ bundle grids) that must be emitted even when sales are zero.

---

## 2. Environment & PyInstaller Storage Resolution

Because the application is packaged into a desktop executable via PyInstaller, the SQLite database must **NEVER** reside in `sys._MEIPASS` (which is a temporary, read-only extraction sandbox).

### 2.1 Database Path Resolver
```python
import os
import sys

def get_database_path(db_name: str = "app_data.db") -> str:
    """
    Resolves the writable database path.
    In packaged executable mode: uses the directory where the .exe resides (or %APPDATA%).
    In development mode: uses the project root directory.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        # Resolve to backend workspace root
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    
    return os.path.join(base_dir, db_name)
```

---

## 3. Database Schema (SQLAlchemy Models)

```python
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, Boolean, DateTime, Date, Index, func
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(String(36), primary_key=True)
    import_batch_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)  # SHOPEE, TIKTOK_SHOP, TOKOPEDIA, LAZADA
    
    # Date grain support (for periodic reports and daily-grain Tinjauan Data)
    transaction_date = Column(Date, nullable=True, index=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    # Labeled Normalized Dimensions
    product_group = Column(String(255), nullable=False, index=True)  # e.g. "Glow Up Tint"
    raw_variant = Column(String(255), nullable=False)
    clean_variant = Column(String(255), nullable=False, index=True)  # e.g. "Active", "Brave"
    is_bundling = Column(Boolean, default=False, nullable=False)
    is_cross_bundling = Column(Boolean, default=False, nullable=False, index=True)  # Bundling Silang
    # SKU-level provenance ONLY: Tinted Jelly Balm ships in a coloured case
    # ("Fizzy Pop", "Sweetie Pop", "Cherry Pop", "Buttered Yellow",
    # "Matcha Strawberry", and any future colour). NULL for every other family.
    #
    # NOT A REPORTING DIMENSION. TJB totals are aggregated by shade across all
    # case colours. Verified against the reference workbook: "Bunny Pink" = 15
    # units spanning four distinct case colours, reported as ONE row. Never
    # include this column in a reporting GROUP BY -- doing so splits one
    # expected row into several. Stored for traceability and future analysis.
    case_color = Column(String(32), nullable=True)
    sku = Column(String(100), nullable=True)

    # Quantitative Metrics (integer IDR: exact, no floating-point drift)
    qty_sold = Column(Integer, nullable=False, default=0)
    revenue = Column(BigInteger, nullable=False, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_transaction_batch_prod_cross", "import_batch_id", "is_cross_bundling", "product_group"),
        Index("ix_transaction_platform_period", "platform", "period_start", "period_end"),
        # Grid population joins on (product_group, clean_variant) within a batch.
        # case_color is excluded -- it is not part of the reporting key.
        Index("ix_transaction_grid_key", "import_batch_id", "product_group", "clean_variant"),
    )


class MappingTemplate(Base):
    __tablename__ = "mapping_templates"

    id = Column(String(36), primary_key=True)
    platform_name = Column(String(50), nullable=False)
    header_signature_hash = Column(String(64), unique=True, nullable=False, index=True)
    column_mapping_json = Column(String, nullable=False)   # Serialized JSON string
    cleaning_rules_json = Column(String, nullable=True)    # Serialized JSON string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
```

---

## 4. SQL Analytics & Aggregation Catalog

All metrics are computed dynamically using parameter-bound SQL queries executed against `transaction_items`.

### Query A: Variant-Level Performance & Contribution (Populates Table 1)
Calculates units sold, total revenue, and the **quantity-share contribution ratio (0–1 scale)** of each variant relative to its master product group:

```sql
WITH product_totals AS (
    SELECT 
        product_group,
        SUM(qty_sold) AS total_product_qty
    FROM transaction_items
    WHERE import_batch_id = :batch_id
    GROUP BY product_group
)
SELECT 
    t.product_group,
    t.clean_variant,
    t.is_bundling,
    t.is_cross_bundling,
    SUM(t.qty_sold) AS total_qty,
    SUM(t.revenue) AS total_revenue,
    CASE
        WHEN pt.total_product_qty > 0
        THEN CAST(SUM(t.qty_sold) AS FLOAT) / pt.total_product_qty
        ELSE 0.0
    END AS contribution_ratio
FROM transaction_items t
JOIN product_totals pt ON t.product_group = pt.product_group
WHERE t.import_batch_id = :batch_id
GROUP BY t.product_group, t.clean_variant, t.is_bundling, t.is_cross_bundling, pt.total_product_qty
ORDER BY t.product_group ASC, t.is_bundling ASC, total_revenue DESC;
```

### Query B: Master Product Group Summary (Populates Table 2)
Summarizes aggregate metrics per master product group and each group's **quantity share (0–1 scale)** of total platform volume:

```sql
WITH grand_total AS (
    SELECT SUM(qty_sold) AS grand_qty
    FROM transaction_items 
    WHERE import_batch_id = :batch_id
)
SELECT 
    product_group,
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue,
    CASE
        WHEN (SELECT grand_qty FROM grand_total) > 0
        THEN CAST(SUM(qty_sold) AS FLOAT) / (SELECT grand_qty FROM grand_total)
        ELSE 0.0
    END AS contribution_ratio
FROM transaction_items
WHERE import_batch_id = :batch_id
GROUP BY product_group
ORDER BY total_revenue DESC;
```

### Query C: Batch List & History Overview
Retrieves aggregated metadata for historical batch management in the UI:
```sql
SELECT 
    import_batch_id,
    platform,
    MIN(period_start) AS period_start,
    MAX(period_end) AS period_end,
    COUNT(DISTINCT product_group) AS total_products,
    SUM(qty_sold) AS grand_total_qty,
    SUM(revenue) AS grand_total_revenue,
    MIN(created_at) AS created_at
FROM transaction_items
GROUP BY import_batch_id, platform
ORDER BY created_at DESC;
```

### Query D: Batch Deletion (Cleanup)
Deletes all records associated with a specific batch ID atomically:
```sql
DELETE FROM transaction_items WHERE import_batch_id = :batch_id;
```

### Query E: Mapping Template Lookup
Retrieves a verified mapping template by its SHA-256 header signature:
```sql
SELECT id, platform_name, header_signature_hash, column_mapping_json, cleaning_rules_json
FROM mapping_templates
WHERE header_signature_hash = :header_signature_hash
LIMIT 1;
```

---

## 5. Repository Data Transfer Objects (DTOs)

All DTOs implement standard camelCase serialization for seamless React TypeScript interop:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from datetime import datetime, date

class BaseDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class VariantPerformanceDTO(BaseDTO):
    product_group: str
    clean_variant: str
    case_color: Optional[str] = None
    is_bundling: bool
    is_cross_bundling: bool = False
    total_qty: int
    total_revenue: float
    contribution_ratio: float  # Quantity share on 0.0 - 1.0 scale

class ProductSummaryDTO(BaseDTO):
    product_group: str
    total_qty: int
    total_revenue: float
    contribution_ratio: float  # Quantity share on 0.0 - 1.0 scale

class BatchSummaryDTO(BaseDTO):
    import_batch_id: str
    platform: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    total_products: int
    grand_total_qty: int
    grand_total_revenue: float
    created_at: datetime
```