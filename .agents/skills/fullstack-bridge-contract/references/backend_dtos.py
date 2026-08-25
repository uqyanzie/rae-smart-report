from enum import Enum
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    """Base Pydantic model with automatic camelCase alias generation and populate-by-name enabled."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class ParentRowIgnoreCondition(str, Enum):
    EQUALS_DASH = "EQUALS_DASH"
    IS_EMPTY = "IS_EMPTY"
    CONTAINS_TOTAL = "CONTAINS_TOTAL"

class IngestionResultDTO(CamelModel):
    file_id: str
    file_name: str
    file_size_bytes: int
    detected_delimiter: str
    available_sheets: List[str]
    active_sheet: str
    total_rows: int
    raw_headers: List[str]
    sample_rows: List[Dict[str, Any]]

class ColumnMappingDTO(CamelModel):
    product_group: str
    raw_variant: str
    qty_sold: str  # Header column name for quantity
    revenue: str   # Header column name for revenue
    sku: Optional[str] = None
    case_color: Optional[str] = None

class ParentRowRuleDTO(CamelModel):
    target_column: str
    ignore_condition: ParentRowIgnoreCondition = ParentRowIgnoreCondition.EQUALS_DASH

class CleaningRuleDTO(CamelModel):
    pattern: str
    replacement: str
    description: str

class ProfilerResponseDTO(CamelModel):
    is_cached: bool
    platform: str
    confidence: float
    column_mapping: ColumnMappingDTO
    parent_row_rule: Optional[ParentRowRuleDTO] = None
    suggested_cleaning_rules: List[CleaningRuleDTO] = []

class TransformAndSaveRequestDTO(CamelModel):
    file_id: str
    active_sheet: Optional[str] = None
    platform: str
    period_start: Optional[str] = None # ISO Date YYYY-MM-DD
    period_end: Optional[str] = None
    column_mapping: ColumnMappingDTO
    parent_row_rule: Optional[ParentRowRuleDTO] = None
    cleaning_rules: List[CleaningRuleDTO] = []
    save_as_template: bool = True

class VariantPerformanceDTO(CamelModel):
    product_group: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool
    total_qty: int
    total_revenue: float
    contribution_ratio: float  # 0-1 unit share
    case_color: Optional[str] = None  # SQL aggregates by shade; always null

class ProductSummaryDTO(CamelModel):
    product_group: str
    total_qty: int
    total_revenue: float
    contribution_ratio: float  # 0-1 unit share

class UnreportedVariantDTO(CamelModel):
    # Persisted non-reportable entry (Query G, is_reported = 0): off-grid
    # variants (standalone 'tidak boleh ecer', 'free gift') and non-catalog
    # product groups. Never appears in report queries or the Produk sheets.
    product_group: str
    clean_variant: str
    raw_variant: str
    total_qty: int
    total_revenue: int

class AggregateRowDTO(CamelModel):
    platform: str
    product_group: str
    clean_variant: str
    total_qty: int
    total_revenue: float
    contribution_ratio: float  # 0-1 unit share

class BatchMetaDTO(CamelModel):
    import_batch_id: str
    platform: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: Optional[datetime] = None

class BatchSummaryDTO(BatchMetaDTO):
    total_products: int
    grand_total_qty: int
    grand_total_revenue: float

class TransformResponseDTO(BatchMetaDTO):
    # Report-boundary (grid-intersected) workbook totals.
    reported_product_count: int
    reported_total_qty: int
    reported_total_revenue: int
    inserted_count: int
    # Dash-row-only excluded volume tally (parent summaries).
    skipped_count: int
    skipped_qty: int
    skipped_revenue: int
    # Persisted non-reportable entries (off-grid variants, non-catalog
    # products); never part of a report figure.
    unreported_count: int
    unreported_qty: int
    unreported_revenue: int
    warning_count: int

class DeleteBatchResponseDTO(CamelModel):
    success: bool
    deleted_count: int
