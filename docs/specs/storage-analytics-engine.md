# Module Specification: Storage & SQL Analytics Engine

## 1. Overview
The Storage module provides persistent local data management using an embedded SQLite database managed via Python (SQLAlchemy / SQLModel). It implements an ELT pattern: normalized and labeled line-item transactions are ingested into atomic tables, while executive reports, summary metrics, and Excel export datasets are computed on-demand through optimized SQL queries (`GROUP BY`, `SUM`, Common Table Expressions).

---

## 2. Environment & PyInstaller Storage Resolution

Because the application is packaged into an executable, the SQLite database must **NEVER** reside in `sys._MEIPASS` (which is a read-only temporary directory).

### 2.1 Database Path Resolver
```python
import os
import sys

def get_database_path(db_name: str = "app_data.db") -> str:
    """
    Resolves the writable database path.
    In packaged executable mode: uses the directory where the .exe resides (or %APPDATA%).
    In development mode: uses the backend root directory.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    
    return os.path.join(base_dir, db_name)

```

## 3. Database Schema (SQLAlchemy Models)
```python
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Index, func
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(String(36), primary_key=True)
    import_batch_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True) # e.g. TIKTOK_SHOP, SHOPEE
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Labeled Normalized Dimensions
    product_group = Column(String(255), nullable=False, index=True) # e.g. "Glow Up Tint"
    raw_variant = Column(String(255), nullable=False)
    clean_variant = Column(String(255), nullable=False, index=True) # e.g. "Active", "Brave"
    is_bundling = Column(Boolean, default=False, nullable=False)
    sku = Column(String(100), nullable=True)

    # Quantitative Metrics
    qty_sold = Column(Integer, nullable=False, default=0)
    revenue = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_transaction_batch_product", "import_batch_id", "product_group"),
        Index("ix_transaction_period", "period_start", "period_end"),
    )


class MappingTemplate(Base):
    __tablename__ = "mapping_templates"

    id = Column(String(36), primary_key=True)
    platform_name = Column(String(50), nullable=False)
    header_signature_hash = Column(String(64), unique=True, nullable=False, index=True)
    column_mapping_json = Column(String, nullable=False)  # Serialized JSON string
    cleaning_rules_json = Column(String, nullable=True)   # Serialized JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

```

## 4. SQL Analytics & Aggregation Catalog
All dashboard tables, charts, and Excel export payloads are generated dynamically using parameter-bound SQL queries executed against transaction_items.

Query A: Variant-Level Performance & Contribution (Table 1)
Calculates units sold, total revenue, and percentage contribution of each variant relative to its master product group:
``` SQL
    WITH product_totals AS (
        SELECT 
            product_group,
            SUM(revenue) AS total_product_revenue
        FROM transaction_items
        WHERE import_batch_id = :batch_id
        GROUP BY product_group
    )
    SELECT 
        t.product_group,
        t.clean_variant,
        t.is_bundling,
        SUM(t.qty_sold) AS total_qty,
        SUM(t.revenue) AS total_revenue,
        ROUND(
            (CAST(SUM(t.revenue) AS FLOAT) / pt.total_product_revenue) * 100.0, 
            2
        ) AS contribution_pct
    FROM transaction_items t
    JOIN product_totals pt ON t.product_group = pt.product_group
    WHERE t.import_batch_id = :batch_id
    GROUP BY t.product_group, t.clean_variant, t.is_bundling, pt.total_product_revenue
    ORDER BY t.product_group ASC, t.is_bundling ASC, total_revenue DESC;
```

Query B: Master Product Group Summary (Table 2)
Summarizes grand performance across distinct master product groups and calculates overall revenue contribution:

``` SQL
    WITH grand_total AS (
        SELECT SUM(revenue) AS grand_revenue 
        FROM transaction_items 
        WHERE import_batch_id = :batch_id
    )
    SELECT 
        product_group,
        SUM(qty_sold) AS total_qty,
        SUM(revenue) AS total_revenue,
        ROUND(
            (CAST(SUM(revenue) AS FLOAT) / (SELECT grand_revenue FROM grand_total)) * 100.0, 
            2
        ) AS contribution_pct
    FROM transaction_items
    WHERE import_batch_id = :batch_id
    GROUP BY product_group
    ORDER BY total_revenue DESC;
```

Query C: Batch List & History Overview
Retrieves aggregated metadata for historical batch viewing in the UI:
``` SQL
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

## 5. Repository Interface Contract (Python / Pydantic)

``` python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VariantPerformanceDTO(BaseModel):
    product_group: str
    clean_variant: str
    is_bundling: bool
    total_qty: int
    total_revenue: float
    contribution_pct: float

class ProductSummaryDTO(BaseModel):
    product_group: str
    total_qty: int
    total_revenue: float
    contribution_pct: float

class BatchSummaryDTO(BaseModel):
    import_batch_id: str
    platform: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    total_products: int
    grand_total_qty: int
    grand_total_revenue: float
    created_at: datetime
```