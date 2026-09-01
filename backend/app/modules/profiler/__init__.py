"""Profiler module package."""

from app.modules.profiler.adapters import (
    BasePlatformAdapter,
    PlatformEnum,
    RawRecord,
    ShopeeAdapter,
    TikTokShopAdapter,
    TokopediaAdapter,
    clean_brand_prefix,
    detect_adapter,
    get_adapter,
    is_parent_or_summary_row,
    parse_tiktok_concatenated_title,
)
from app.modules.profiler.fallback import (
    CamelModel,
    CleaningRule,
    ColumnMapping,
    ParentRowIgnoreCondition,
    ParentRowRule,
    ProfilerResult,
    compute_header_signature,
    profile_spreadsheet_headers,
)

__all__ = [
    "BasePlatformAdapter",
    "CamelModel",
    "CleaningRule",
    "ColumnMapping",
    "ParentRowIgnoreCondition",
    "ParentRowRule",
    "PlatformEnum",
    "ProfilerResult",
    "RawRecord",
    "ShopeeAdapter",
    "TikTokShopAdapter",
    "TokopediaAdapter",
    "clean_brand_prefix",
    "compute_header_signature",
    "detect_adapter",
    "get_adapter",
    "is_parent_or_summary_row",
    "parse_tiktok_concatenated_title",
    "profile_spreadsheet_headers",
]
