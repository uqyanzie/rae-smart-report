from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib
import json

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

class ColumnMapping(BaseModel):
    productGroup: str = Field(description="Column name corresponding to master product title or group")
    rawVariant: str = Field(description="Column name corresponding to product variation or model")
    qtySold: str = Field(description="Column name corresponding to units/quantity sold")
    revenue: str = Field(description="Column name corresponding to gross or net sales revenue")
    sku: Optional[str] = Field(default=None, description="Column name for SKU identifier, if present")

class ParentRowRule(BaseModel):
    targetColumn: str = Field(description="Column to inspect for parent/subtotal indicator")
    ignoreCondition: ParentRowIgnoreCondition = Field(description="Condition under which the row must be dropped")

class CleaningRule(BaseModel):
    pattern: str = Field(description="Regular expression pattern to strip or replace")
    replacement: str = Field(default="", description="Replacement string")
    description: str = Field(description="Reason or rationale for cleaning rule")

class ProfilerResult(BaseModel):
    platform: PlatformEnum
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    columnMapping: ColumnMapping
    parentRowRule: ParentRowRule
    suggestedCleaningRules: List[CleaningRule] = Field(default_factory=list)

def compute_header_signature(headers: List[str]) -> str:
    """
    Computes a canonical SHA-256 hash signature from a list of raw column headers.
    Normalizes headers by lowercasing, sorting, and stripping whitespace.
    """
    normalized = [str(h).strip().lower() for h in headers if str(h).strip()]
    normalized_json = json.dumps(sorted(normalized), separators=(',', ':'))
    return hashlib.sha256(normalized_json.encode('utf-8')).hexdigest()
