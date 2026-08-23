from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
import hashlib
import json

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class PlatformEnum(str, Enum):
    TIKTOK_SHOP = "TIKTOK_SHOP"
    SHOPEE = "SHOPEE"
    TOKOPEDIA = "TOKOPEDIA"
    LAZADA = "LAZADA"
    BLIBLI = "BLIBLI"
    UNKNOWN = "UNKNOWN"

class ParentRowIgnoreCondition(str, Enum):
    EQUALS_DASH = "EQUALS_DASH"
    IS_EMPTY = "IS_EMPTY"
    CONTAINS_TOTAL = "CONTAINS_TOTAL"

class ColumnMapping(CamelModel):
    product_group: str = Field(description="Column name corresponding to master product title or group")
    raw_variant: str = Field(description="Column name corresponding to product variation or model")
    qty_sold: str = Field(description="Column name corresponding to units/quantity sold (ready-to-ship/delivered)")
    revenue: str = Field(description="Column name corresponding to gross or net sales revenue (ready-to-ship/delivered)")
    sku: Optional[str] = Field(default=None, description="Column name for SKU identifier, if present")

class ParentRowRule(CamelModel):
    target_column: str = Field(description="Column to inspect for parent/subtotal indicator")
    ignore_condition: ParentRowIgnoreCondition = Field(description="Condition under which the row must be dropped")

class CleaningRule(CamelModel):
    pattern: str = Field(description="Regular expression pattern to strip or replace")
    replacement: str = Field(default="", description="Replacement string")
    description: str = Field(description="Reason or rationale for cleaning rule")

class ProfilerResult(CamelModel):
    platform: PlatformEnum
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    column_mapping: ColumnMapping
    parent_row_rule: Optional[ParentRowRule] = Field(
        default=None,
        description="Parent row elimination rule for platforms with header/summary rows (null if format is atomic like TikTok Shop)"
    )
    suggested_cleaning_rules: List[CleaningRule] = Field(default_factory=list)

def compute_header_signature(headers: List[str]) -> str:
    """
    Computes a canonical SHA-256 hash signature from a list of raw column headers.
    Normalizes headers by lowercasing, sorting, and stripping whitespace.
    Note: Sorting ensures order-independent template matching across platform export variants.
    """
    normalized = [str(h).strip().lower() for h in headers if str(h).strip()]
    normalized_json = json.dumps(sorted(normalized), separators=(',', ':'))
    return hashlib.sha256(normalized_json.encode('utf-8')).hexdigest()
