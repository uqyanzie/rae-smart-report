from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class IngestionResultDTO(BaseModel):
    file_id: str
    file_name: str
    file_size_bytes: int
    detected_delimiter: str
    available_sheets: List[str]
    active_sheet: str
    total_rows: int
    raw_headers: List[str]
    sample_rows: List[Dict[str, Any]]

class ColumnMappingDTO(BaseModel):
    product_group: str
    raw_variant: str
    qty_sold: str
    revenue: str
    sku: Optional[str] = None

class ParentRowRuleDTO(BaseModel):
    target_column: str
    ignore_condition: str # "EQUALS_DASH" | "IS_EMPTY" | "CONTAINS_TOTAL"

class CleaningRuleDTO(BaseModel):
    pattern: str
    replacement: str
    description: str

class ProfilerResponseDTO(BaseModel):
    is_cached: bool
    platform: str
    confidence: float
    column_mapping: ColumnMappingDTO
    parent_row_rule: ParentRowRuleDTO
    suggested_cleaning_rules: List[CleaningRuleDTO]

class TransformAndSaveRequestDTO(BaseModel):
    file_id: str
    active_sheet: Optional[str] = None
    platform: str
    period_start: Optional[str] = None # ISO Date YYYY-MM-DD
    period_end: Optional[str] = None
    column_mapping: ColumnMappingDTO
    parent_row_rule: ParentRowRuleDTO
    cleaning_rules: List[CleaningRuleDTO]
    save_as_template: bool = True

class VariantPerformanceDTO(BaseModel):
    product_group: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool
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
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    total_products: int
    grand_total_qty: int
    grand_total_revenue: float
    created_at: str
