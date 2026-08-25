"""SHA-256 header signature computation and schema profiler models."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.modules.profiler.adapters import (
    PlatformEnum,
    ShopeeAdapter,
    TikTokShopAdapter,
    detect_adapter,
)


class CamelModel(BaseModel):
    """Base model with camelCase serialization for bridge contract."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ParentRowIgnoreCondition(StrEnum):
    """Conditions under which a parent/summary row must be pruned."""

    EQUALS_DASH = "EQUALS_DASH"
    IS_EMPTY = "IS_EMPTY"
    CONTAINS_TOTAL = "CONTAINS_TOTAL"


class ColumnMapping(CamelModel):
    """Mapping from canonical field names to raw spreadsheet column headers."""

    product_group: str = Field(description="Column name corresponding to master product title or group")
    raw_variant: str = Field(description="Column name corresponding to product variation or model")
    qty_sold: str = Field(
        description="Column name corresponding to units/quantity sold (ready-to-ship/delivered)"
    )
    revenue: str = Field(
        description="Column name corresponding to gross or net sales revenue (ready-to-ship/delivered)"
    )
    sku: str | None = Field(default=None, description="Column name for SKU identifier, if present")
    case_color: str | None = Field(
        default=None, description="Column name for 3D case color identifier, if present"
    )


class ParentRowRule(CamelModel):
    """Rule defining how parent/summary rows should be identified and pruned."""

    target_column: str = Field(description="Column to inspect for parent/subtotal indicator")
    ignore_condition: ParentRowIgnoreCondition = Field(
        description="Condition under which the row must be dropped"
    )


class CleaningRule(CamelModel):
    """Deterministic regex cleaning rule."""

    pattern: str = Field(description="Regular expression pattern to match")
    replacement: str = Field(default="", description="Replacement string")
    description: str = Field(default="", description="Reason or rationale for cleaning rule")


class ProfilerResult(CamelModel):
    """Result of spreadsheet schema profiling."""

    platform: PlatformEnum
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    column_mapping: ColumnMapping
    parent_row_rule: ParentRowRule | None = Field(
        default=None,
        description="Parent row elimination rule (null if export is atomic like TikTok Shop)",
    )
    suggested_cleaning_rules: list[CleaningRule] = Field(default_factory=list)


def compute_header_signature(headers: list[str]) -> str:
    """
    Computes a canonical SHA-256 hash signature from a list of raw column headers.
    Normalizes headers by lowercasing, sorting, and stripping whitespace.
    Sorting ensures order-independent template matching across export variations.
    """
    normalized = [str(h).strip().lower() for h in headers if str(h).strip()]
    normalized_json = json.dumps(sorted(normalized), separators=(",", ":"))
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


def profile_spreadsheet_headers(headers: list[str], sheet_name: str | None = None) -> ProfilerResult:
    """
    Deterministically profiles spreadsheet headers, returning known platform mappings
    or an UNKNOWN profile for human / template resolution.
    """
    adapter = detect_adapter(headers, sheet_name)

    if isinstance(adapter, ShopeeAdapter):
        return ProfilerResult(
            platform=PlatformEnum.SHOPEE,
            confidence=1.0,
            column_mapping=ColumnMapping(
                product_group=ShopeeAdapter.COL_PROD,
                raw_variant=ShopeeAdapter.COL_VAR,
                sku=ShopeeAdapter.COL_SKU,
                qty_sold=ShopeeAdapter.COL_QTY,
                revenue=ShopeeAdapter.COL_REV,
            ),
            parent_row_rule=ParentRowRule(
                target_column=ShopeeAdapter.COL_VAR,
                ignore_condition=ParentRowIgnoreCondition.EQUALS_DASH,
            ),
            suggested_cleaning_rules=[
                CleaningRule(
                    pattern=r"^\d+\.\s*",
                    replacement="",
                    description="Strip ordinal prefix numbers like '05. Dynamic'",
                ),
                CleaningRule(
                    pattern=r"[/,]\s*(random keychain|tanpa keychain|free gift|free pouch|gift).*$",
                    replacement="",
                    description="Strip marketing and packaging suffixes",
                ),
            ],
        )

    elif isinstance(adapter, TikTokShopAdapter):
        return ProfilerResult(
            platform=PlatformEnum.TIKTOK_SHOP,
            confidence=1.0,
            column_mapping=ColumnMapping(
                product_group=TikTokShopAdapter.COL_PROD,
                raw_variant=TikTokShopAdapter.COL_PROD,  # Split by ':' during ingestion
                sku=TikTokShopAdapter.COL_SKU,
                qty_sold=TikTokShopAdapter.COL_QTY,
                revenue=TikTokShopAdapter.COL_REV,
            ),
            parent_row_rule=None,  # TikTok Shop has zero parent rows (atomic SKU-level)
            suggested_cleaning_rules=[
                CleaningRule(
                    pattern=r"[/,]\s*(random keychain|tanpa keychain|free gift|free pouch|gift).*$",
                    replacement="",
                    description="Strip marketing and packaging suffixes",
                ),
            ],
        )

    # Unknown schema fallback
    return ProfilerResult(
        platform=PlatformEnum.UNKNOWN,
        confidence=0.0,
        column_mapping=ColumnMapping(
            product_group="",
            raw_variant="",
            qty_sold="",
            revenue="",
            sku=None,
        ),
        parent_row_rule=None,
        suggested_cleaning_rules=[],
    )
