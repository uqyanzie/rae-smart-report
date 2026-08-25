"""API data transfer objects, all serialized strictly camelCase.

The ``CamelModel`` base is reused from the profiler module (single bridge
contract definition, per the fullstack-bridge-contract skill); it provides
``alias_generator=to_camel``, ``populate_by_name=True`` and
``from_attributes=True``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.modules.profiler.fallback import CamelModel, ParentRowIgnoreCondition

__all__ = [
    "AggregateRowDTO",
    "BatchMetaDTO",
    "BatchSummaryDTO",
    "CamelModel",
    "CleaningRuleDTO",
    "ColumnMappingDTO",
    "DeleteBatchResponseDTO",
    "IngestionResultDTO",
    "ParentRowIgnoreCondition",
    "ParentRowRuleDTO",
    "ProductSummaryDTO",
    "ProfileRequestDTO",
    "ProfilerResponseDTO",
    "TransformAndSaveRequestDTO",
    "TransformResponseDTO",
    "UnreportedVariantDTO",
    "VariantPerformanceDTO",
]


class IngestionResultDTO(CamelModel):
    """Result of uploading and structurally inspecting a spreadsheet."""

    file_id: str
    file_name: str
    file_size_bytes: int
    detected_delimiter: str | None = None
    available_sheets: list[str] = Field(default_factory=list)
    active_sheet: str
    total_rows: int
    raw_headers: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)


class ColumnMappingDTO(CamelModel):
    """Mapping from canonical field names to raw spreadsheet column headers."""

    product_group: str
    raw_variant: str
    qty_sold: str
    revenue: str
    sku: str | None = None
    case_color: str | None = None


class ParentRowRuleDTO(CamelModel):
    """Rule identifying parent/summary rows to prune."""

    target_column: str
    ignore_condition: ParentRowIgnoreCondition


class CleaningRuleDTO(CamelModel):
    """Deterministic regex cleaning rule."""

    pattern: str
    replacement: str = ""
    description: str = ""


class ProfilerResponseDTO(CamelModel):
    """Platform detection outcome for a header signature."""

    is_cached: bool
    platform: str
    confidence: float
    column_mapping: ColumnMappingDTO
    parent_row_rule: ParentRowRuleDTO | None = None
    suggested_cleaning_rules: list[CleaningRuleDTO] = Field(default_factory=list)


class ProfileRequestDTO(CamelModel):
    """Body for the profile endpoint."""

    file_id: str
    active_sheet: str | None = None


class TransformAndSaveRequestDTO(CamelModel):
    """Body for the transform-and-save pipeline.

    ``period_start`` / ``period_end`` are optional ISO dates supplied by the
    user; the route expands them to day-bounded datetimes for persistence.
    """

    file_id: str
    active_sheet: str | None = None
    platform: str
    period_start: date | None = None
    period_end: date | None = None
    column_mapping: ColumnMappingDTO
    parent_row_rule: ParentRowRuleDTO | None = None
    cleaning_rules: list[CleaningRuleDTO] = Field(default_factory=list)
    save_as_template: bool = True


class VariantPerformanceDTO(CamelModel):
    """Variant-level performance row (report Table 1)."""

    product_group: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool
    total_qty: int
    total_revenue: int
    contribution_ratio: float
    # SQL aggregates by shade, so case color is never a grouping key; the
    # field is retained for contract parity and serializes null.
    case_color: str | None = None


class ProductSummaryDTO(CamelModel):
    """Master product group rollup (report Table 2)."""

    product_group: str
    total_qty: int
    total_revenue: int
    contribution_ratio: float


class UnreportedVariantDTO(CamelModel):
    """Persisted non-reportable entry (Query G, ``is_reported == 0``).

    Covers off-grid variants (standalone 'tidak boleh ecer', 'free gift',
    etc.) and non-catalog product groups. Stored for traceability and shown on
    the dashboard / 'Tidak Terlaporkan S/T' export sheets; never appears in a
    report query or the four Produk sheets. ``raw_variant`` carries the full
    original label for provenance.
    """

    product_group: str
    clean_variant: str
    raw_variant: str
    total_qty: int
    total_revenue: int


class AggregateRowDTO(CamelModel):
    """Multi-batch / multi-platform / date-range aggregation row (Query C).

    Groups by (platform, product_group, clean_variant) across every persisted
    batch matching the optional platform / period / cross-bundling filters;
    ``contribution_ratio`` is the 0-1 unit share against the filtered grand
    total quantity.
    """

    platform: str
    product_group: str
    clean_variant: str
    total_qty: int
    total_revenue: int
    contribution_ratio: float


class BatchMetaDTO(CamelModel):
    """Shared batch identity/metadata carried by every batch-shaped response."""

    import_batch_id: str
    platform: str
    # batch_history() returns parsed datetimes (never date-only), so datetime
    # is used to avoid Pydantic's inexact date-from-datetime rejection.
    period_start: datetime | None = None
    period_end: datetime | None = None
    created_at: datetime | None = None


class BatchSummaryDTO(BatchMetaDTO):
    """Storage-level batch summary row (Query D raw transaction sums).

    ``total_products`` / ``grand_total_*`` are whole-batch figures including
    cross-bundling rows; they are NOT the workbook (grid-intersected) totals.
    """

    total_products: int
    grand_total_qty: int
    grand_total_revenue: int


class TransformResponseDTO(BatchMetaDTO):
    """Report-boundary batch summary plus persistence audit details.

    ``reported_*`` mirrors the Produk workbook (grid-intersected,
    ``is_reported = 1``), distinct from the storage-level ``grandTotal*``
    figures on ``/reports/batches`` (R5). ``skipped_*`` is now the dash-only
    excluded tally (parent summaries). ``unreported_*`` is the persisted
    non-reportable volume (off-grid variants, non-catalog products) -- stored
    and viewable via ``/unreported`` but never part of a report figure.
    """

    reported_product_count: int
    reported_total_qty: int
    reported_total_revenue: int
    inserted_count: int
    skipped_count: int
    skipped_qty: int
    skipped_revenue: int
    unreported_count: int
    unreported_qty: int
    unreported_revenue: int
    warning_count: int


class DeleteBatchResponseDTO(CamelModel):
    """Outcome of batch deletion."""

    success: bool
    deleted_count: int
