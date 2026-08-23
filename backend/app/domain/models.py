"""Pure domain models for RAE Smart Report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    sku: Optional[str] = None
    case_color: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GridRow:
    """Represents a row in the declarative product report grid."""

    product_group: str
    clean_variant: str
    is_bundling: bool
    is_cross_bundling: bool
    expected_label: str
    case_color: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ReportGroup:
    """Represents a report section/group."""

    name: str
    is_bundling: bool
    is_cross: bool
    family_name: Optional[str] = None
