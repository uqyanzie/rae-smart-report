"""Pure domain models for RAE Smart Report."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VariantRecord:
    """Represents a normalized atomic transaction item in domain space."""

    platform: str
    product_group: str
    raw_variant: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool
    qty_sold: int
    revenue: int
    sku: str | None = None
    case_color: str | None = None
    # Raw source product column value (verbatim from the spreadsheet), kept
    # for provenance so an unreported row can be traced back to its origin.
    raw_product: str | None = None


@dataclass(frozen=True, slots=True)
class GridRow:
    """Represents a row in the declarative product report grid."""

    product_group: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool
    expected_label: str
    case_color: str | None = None


@dataclass(frozen=True, slots=True)
class ReportGroup:
    """Represents a report section/group."""

    name: str
    is_bundling: bool
    is_cross: bool
    family_name: str | None = None
